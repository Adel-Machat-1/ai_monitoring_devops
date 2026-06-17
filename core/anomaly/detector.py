import os
import io
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib
from datetime import datetime

import logging
logger = logging.getLogger(__name__)

# ── MinIO ─────────────────────────────────────────────────────
from config import MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY
from minio import Minio
from minio.error import S3Error

MINIO_BUCKET_MODELS = "ml-models"

def _get_minio():
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False
    )

def _ensure_bucket():
    try:
        client = _get_minio()
        if not client.bucket_exists(MINIO_BUCKET_MODELS):
            client.make_bucket(MINIO_BUCKET_MODELS)
            logger.info(f"[DETECTOR] Bucket {MINIO_BUCKET_MODELS} créé")
    except Exception as e:
        logger.warning(f"[DETECTOR] Erreur bucket MinIO: {e}")

# ── Dossier local pour cache ───────────────────────────────────
MODELS_DIR = "models"
os.makedirs(MODELS_DIR, exist_ok=True)

# ── Historique des métriques ───────────────────────────────────
metrics_history = {app: [] for app in ["keycloak", "postgresql", "mongodb", "redis", "redpanda"]}

MIN_TRAINING_POINTS = 10
CONTAMINATION       = 0.03
MIN_ANOMALY_SCORE   = 0.70


def add_to_history(app_name, metrics_data):
    metrics_history[app_name].append(metrics_data)
    if len(metrics_history[app_name]) > 500:
        metrics_history[app_name] = metrics_history[app_name][-500:]


def get_features(app_name):
    history = metrics_history[app_name]
    if not history:
        return None
    df = pd.DataFrame(history)
    df = df.fillna(0)
    return df.values


def _save_to_minio(app_name, filename):
    """Sauvegarde un fichier .pkl local vers MinIO"""
    try:
        client     = _get_minio()
        local_path = f"{MODELS_DIR}/{filename}"
        object_name = f"{app_name}/{filename}"

        client.fput_object(MINIO_BUCKET_MODELS, object_name, local_path)
        logger.info(f"[DETECTOR] ✅ Modèle sauvegardé dans MinIO : {object_name}")
    except Exception as e:
        logger.warning(f"[DETECTOR] ⚠️ Erreur sauvegarde MinIO {filename}: {e}")


def _load_from_minio(app_name, filename):
    """Charge un fichier .pkl depuis MinIO vers le cache local"""
    try:
        client      = _get_minio()
        local_path  = f"{MODELS_DIR}/{filename}"
        object_name = f"{app_name}/{filename}"

        client.fget_object(MINIO_BUCKET_MODELS, object_name, local_path)
        logger.info(f"[DETECTOR] ✅ Modèle chargé depuis MinIO : {object_name}")
        return True
    except S3Error as e:
        if e.code == "NoSuchKey":
            logger.info(f"[DETECTOR] Modèle non trouvé dans MinIO : {app_name}/{filename}")
        else:
            logger.warning(f"[DETECTOR] ⚠️ Erreur MinIO {filename}: {e}")
        return False
    except Exception as e:
        logger.warning(f"[DETECTOR] ⚠️ Erreur chargement MinIO {filename}: {e}")
        return False


def train_model(app_name):
    """Entraîne le modèle Isolation Forest et sauvegarde dans MinIO"""
    features = get_features(app_name)

    if features is None or len(features) < MIN_TRAINING_POINTS:
        logger.info(f"[DETECTOR] {app_name} — pas assez de données ({len(features) if features is not None else 0}/{MIN_TRAINING_POINTS})")
        return None

    logger.info(f"[DETECTOR] Entraînement du modèle pour {app_name} ({len(features)} points)...")

    scaler          = StandardScaler()
    features_scaled = scaler.fit_transform(features)

    model = IsolationForest(
        contamination=CONTAMINATION,
        random_state=42,
        n_estimators=100
    )
    model.fit(features_scaled)

    # Sauvegarder localement
    joblib.dump(model,  f"{MODELS_DIR}/{app_name}_model.pkl")
    joblib.dump(scaler, f"{MODELS_DIR}/{app_name}_scaler.pkl")

    # Sauvegarder dans MinIO
    _ensure_bucket()
    _save_to_minio(app_name, f"{app_name}_model.pkl")
    _save_to_minio(app_name, f"{app_name}_scaler.pkl")

    logger.info(f"[DETECTOR] ✅ Modèle {app_name} entraîné et sauvegardé")
    return model


def load_model(app_name):
    """Charge un modèle — depuis cache local ou MinIO"""
    model_path  = f"{MODELS_DIR}/{app_name}_model.pkl"
    scaler_path = f"{MODELS_DIR}/{app_name}_scaler.pkl"

    # 1. Cache local
    if os.path.exists(model_path) and os.path.exists(scaler_path):
        model  = joblib.load(model_path)
        scaler = joblib.load(scaler_path)
        return model, scaler

    # 2. MinIO fallback
    logger.info(f"[DETECTOR] Chargement depuis MinIO pour {app_name}...")
    model_ok  = _load_from_minio(app_name, f"{app_name}_model.pkl")
    scaler_ok = _load_from_minio(app_name, f"{app_name}_scaler.pkl")

    if model_ok and scaler_ok:
        model  = joblib.load(model_path)
        scaler = joblib.load(scaler_path)
        return model, scaler

    return None, None


def detect_anomaly(app_name, current_metrics):
    model, scaler = load_model(app_name)

    if model is None:
        model = train_model(app_name)
        if model is None:
            return False, 0.0, "Pas assez de données pour la détection"
        _, scaler = load_model(app_name)

    try:
        features        = np.array(list(current_metrics.values())).reshape(1, -1)
        features_scaled = scaler.transform(features)

        prediction    = model.predict(features_scaled)[0]
        score         = model.score_samples(features_scaled)[0]
        anomaly_score = max(0.0, min(1.0, -score))
        is_anomaly    = prediction == -1

        if is_anomaly and anomaly_score < MIN_ANOMALY_SCORE:
            logger.info(f"  [{app_name}] Score {anomaly_score:.2f} < {MIN_ANOMALY_SCORE} → faux positif ignoré")
            is_anomaly = False

        if is_anomaly:
            reason = f"Score d'anomalie : {anomaly_score:.2f} — comportement inhabituel détecté"
        else:
            reason = f"Normal (score: {anomaly_score:.2f})"

        return is_anomaly, anomaly_score, reason

    except Exception as e:
        logger.info(f"[DETECTOR] Erreur détection {app_name}: {str(e)}")
        return False, 0.0, str(e)


def process_collected_metrics(all_metrics):
    anomalies = []

    for app_name in ["keycloak", "postgresql", "mongodb", "redis", "redpanda"]:
        app_metrics = all_metrics.get(app_name, {})
        if not app_metrics:
            continue

        add_to_history(app_name, app_metrics)
        is_anomaly, score, reason = detect_anomaly(app_name, app_metrics)

        status = "🔴 ANOMALIE" if is_anomaly else "✅ Normal"
        logger.info(f"  [{app_name}] {status} — {reason}")

        if is_anomaly:
            anomalies.append({
                "app":     app_name,
                "score":   score,
                "reason":  reason,
                "metrics": app_metrics,
            })

    return anomalies