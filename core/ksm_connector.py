import time
import logging
import requests
from datetime import datetime, timezone
from config import KSM_BASE_URL, KSM_EMAIL, KSM_PASSWORD, KSM_ENABLED

logger = logging.getLogger(__name__)

_jwt_token = None
_token_obtained_at = 0
TOKEN_TTL = 3600  # 1 heure


def _login():
    """Authentifie le service account sur KSM et met en cache le JWT."""
    global _jwt_token, _token_obtained_at

    try:
        response = requests.post(
            f"{KSM_BASE_URL}/api/login",
            json={"email": KSM_EMAIL, "password": KSM_PASSWORD},
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=10,
        )
        response.raise_for_status()
        token = response.json().get("token")
        if not token:
            logger.info("[KSM] ❌ Réponse login sans token")
            return None
        _jwt_token = token
        _token_obtained_at = time.time()
        logger.info("[KSM] ✅ Authentifié — JWT obtenu")
        return _jwt_token
    except requests.exceptions.ConnectionError:
        logger.info(f"[KSM] 🔌 Impossible de joindre {KSM_BASE_URL}")
        return None
    except Exception as e:
        logger.info(f"[KSM] ❌ Échec authentification : {e}")
        return None


def _get_token():
    """Retourne le JWT en cache ou se ré-authentifie si expiré."""
    global _jwt_token, _token_obtained_at
    if _jwt_token and (time.time() - _token_obtained_at) < TOKEN_TTL:
        return _jwt_token
    return _login()


def _build_type(parsed):
    """Génère un type dynamique selon le nom de l'alerte détectée."""
    name = parsed.get("name", "")

    if name.startswith("AnomalyDetected_"):
        service = name.replace("AnomalyDetected_", "").lower()
        return f"anomaly-{service}"

    type_map = {
        "PostgresDown"             : "service-down",
        "MongoDBDown"              : "service-down",
        "RedisDown"                : "service-down",
        "RedpandaDown"             : "service-down",
        "KeycloakDown"             : "service-down",
        "PostgresPodNotRunning"    : "pod-not-running",
        "MongoPodNotRunning"       : "pod-not-running",
        "RedisPodNotRunning"       : "pod-not-running",
        "RedpandaPodNotRunning"    : "pod-not-running",
        "KeycloakPodNotRunning"    : "pod-not-running",
        "AppCrashLooping"          : "crash-loop",
        "AppDeploymentUnavailable" : "deployment-unavailable",
        "AppPodNotReady"           : "pod-not-ready",
    }

    return type_map.get(name, "incident")


def _build_description(parsed):
    """Construit une description lisible depuis les données de l'alerte."""
    name      = parsed.get("name", "unknown")
    service   = parsed.get("service", "unknown")
    severity  = parsed.get("severity", "unknown").upper()
    namespace = parsed.get("namespace", "unknown")
    pods      = ", ".join(parsed.get("affected_pods", [])) or "N/A"
    detail    = parsed.get("description") or parsed.get("summary") or ""

    desc = (
        f"[{severity}] {name} — service: {service} "
        f"(namespace: {namespace}, pods: {pods})"
    )
    if detail:
        desc += f". {detail}"
    return desc.strip()[:250] 


def send_alarm_to_ksm(parsed, report_url=None, max_retries=3):
    """
    Envoie une alarme d'incident base de données vers le backend KSM.
    report_url : URL MinIO du rapport PDF généré par l'agent IA (optionnel).
    Retourne True si l'envoi a réussi, False sinon.
    """
    if not KSM_ENABLED:
        logger.info("[KSM] ⏭️ Intégration KSM désactivée (KSM_ENABLED=False)")
        return False

    # Normaliser triggered_at en ISO 8601 UTC
    triggered_at = parsed.get("started_at")
    if not triggered_at:
        triggered_at = datetime.now(timezone.utc).isoformat()

    payload = {
        "description":  _build_description(parsed)[:250],
        "type":         _build_type(parsed)[:100],
        "triggered_at": triggered_at,
        "report_url":   report_url[:500] if report_url else None,
        }

    logger.info(f"\n[KSM] Envoi alarme → {parsed['name']} ({parsed.get('severity','?').upper()})")
    logger.info(f"[KSM] Description : {payload['description'][:120]}...")

    for attempt in range(1, max_retries + 1):
        token = _get_token()
        if not token:
            logger.info(f"[KSM] ❌ Aucun token disponible — tentative {attempt}/{max_retries}")
            time.sleep(5)
            continue

        try:
            response = requests.post(
                f"{KSM_BASE_URL}/api/alarms",
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type":  "application/json",
                    "Accept":        "application/json",
                },
                timeout=15,
            )

            # Token expiré → forcer re-login
            if response.status_code == 401:
                global _jwt_token
                _jwt_token = None
                logger.info("[KSM] 🔄 Token expiré — re-login au prochain essai")
                continue

            if response.status_code in (200, 201):
                logger.info(f"[KSM] ✅ Alarme créée dans KSM (HTTP {response.status_code})")
                return True

            logger.info(
                f"[KSM] ⚠️ HTTP {response.status_code} — "
                f"{response.text[:200]}"
            )

        except requests.exceptions.Timeout:
            logger.info(f"[KSM] ⏱️ Timeout — tentative {attempt}/{max_retries}")
        except requests.exceptions.ConnectionError:
            logger.info(f"[KSM] 🔌 Connexion refusée — tentative {attempt}/{max_retries}")
        except Exception as e:
            logger.info(f"[KSM] ❌ Erreur inattendue : {e}")

        if attempt < max_retries:
            wait = attempt * 5
            logger.info(f"[KSM] Attente {wait}s avant retry...")
            time.sleep(wait)

    logger.info(f"[KSM] ❌ Alarme non envoyée après {max_retries} tentatives — {parsed['name']}")
    return False
