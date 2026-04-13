import subprocess
import json
from datetime import datetime

def get_kubernetes_events(pod=None, namespace="apps", max_events=20):
    """
    Récupère les events Kubernetes pour un pod ou namespace
    Fonctionne pour les 2 systèmes : alerte + anomaly detection
    """
    try:
        events = []

        # ── Query 1 : events du pod spécifique ───────────────
        if pod:
            cmd = [
                "kubectl", "get", "events",
                "-n", namespace,
                "--field-selector", f"involvedObject.name={pod}",
                "-o", "json"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                data = json.loads(result.stdout)
                for item in data.get("items", []):
                    events.append({
                        "type":      item.get("type", "Unknown"),
                        "reason":    item.get("reason", "Unknown"),
                        "message":   item.get("message", ""),
                        "object":    item.get("involvedObject", {}).get("name", ""),
                        "count":     item.get("count", 1),
                        "last_seen": item.get("lastTimestamp", ""),
                    })

        # ── Query 2 : si pas de pod ou pas d'events → namespace ──
        if not events:
            cmd = [
                "kubectl", "get", "events",
                "-n", namespace,
                "--field-selector", "type=Warning",
                "-o", "json"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                data  = json.loads(result.stdout)
                items = data.get("items", [])

                # Trier par date (plus récent en premier)
                items.sort(
                    key=lambda x: x.get("lastTimestamp", ""),
                    reverse=True
                )

                for item in items[:max_events]:
                    events.append({
                        "type":      item.get("type", "Unknown"),
                        "reason":    item.get("reason", "Unknown"),
                        "message":   item.get("message", ""),
                        "object":    item.get("involvedObject", {}).get("name", ""),
                        "count":     item.get("count", 1),
                        "last_seen": item.get("lastTimestamp", ""),
                    })

        if events:
            print(f"[EVENTS] ✅ {len(events)} event(s) trouvé(s) pour {pod or namespace}")
        else:
            print(f"[EVENTS] ℹ️ Aucun event pour {pod or namespace}")

        return events

    except subprocess.TimeoutExpired:
        print(f"[EVENTS] ⚠️ Timeout kubectl")
        return []
    except Exception as e:
        print(f"[EVENTS] ❌ Erreur : {str(e)}")
        return []


def format_events_text(events, max_events=20):
    """
    Formate les events en texte lisible pour GPT-4
    Utilisé par les 2 systèmes
    """
    if not events:
        return "Aucun event Kubernetes disponible."

    lines = []
    for e in events[:max_events]:
        # Formater la date
        last_seen = e.get("last_seen", "")
        if last_seen:
            try:
                dt = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
                last_seen = dt.strftime("%H:%M:%S")
            except:
                pass

        emoji = "⚠️" if e["type"] == "Warning" else "✅"
        line  = (
            f"{emoji} [{last_seen}] {e['type']} | "
            f"{e['reason']} | "
            f"{e['object']} | "
            f"{e['message'][:100]}"  # limiter la longueur
        )
        lines.append(line)

    return "\n".join(lines)