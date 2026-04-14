import os
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib
from datetime import datetime

# Dossier pour sauvegarder les modèles entraînés
MODELS_DIR = "models"
os.makedirs(MODELS_DIR, exist_ok=True)

# Historique des métriques collectées (en mémoire)
metrics_history = {app: [] for app in ["keycloak", "postgresql", "mongodb", "redis", "redpanda"]}

# Nombre minimum de points pour entraîner le modèle
MIN_TRAINING_POINTS = 5  # ~50 minutes de données (10 x 5min)

# Seuil de contamination (% attendu d'anomalies)
CONTAMINATION = 0.03  # 3%

def add_to_history(app_name, metrics_data):
    """Ajoute les métriques dans l'historique"""
    metrics_history[app_name].append(metrics_data)

    # Garder seulement les 500 derniers points (~42 heures)
    if len(metrics_history[app_name]) > 500:
        metrics_history[app_name] = metrics_history[app_name][-500:]

def get_features(app_name):
    """Retourne les métriques sous forme de tableau numpy"""
    history = metrics_history[app_name]
    if not history:
        return None

    df = pd.DataFrame(history)
    df = df.fillna(0)
    return df.values

def train_model(app_name):
    """Entraîne le modèle Isolation Forest pour une app"""
    features = get_features(app_name)

    if features is None or len(features) < MIN_TRAINING_POINTS:
        print(f"[DETECTOR] {app_name} — pas assez de données ({len(features) if features is not None else 0}/{MIN_TRAINING_POINTS})")
        return None

    print(f"[DETECTOR] Entraînement du modèle pour {app_name} ({len(features)} points)...")

    # Normalisation
    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features)

    # Entraînement Isolation Forest
    model = IsolationForest(
        contamination=CONTAMINATION,
        random_state=42,
        n_estimators=100
    )
    model.fit(features_scaled)

    # Sauvegarder le modèle et le scaler
    joblib.dump(model,  f"{MODELS_DIR}/{app_name}_model.pkl")
    joblib.dump(scaler, f"{MODELS_DIR}/{app_name}_scaler.pkl")

    print(f"[DETECTOR] ✅ Modèle {app_name} entraîné et sauvegardé")
    return model

def load_model(app_name):
    """Charge un modèle sauvegardé"""
    model_path  = f"{MODELS_DIR}/{app_name}_model.pkl"
    scaler_path = f"{MODELS_DIR}/{app_name}_scaler.pkl"

    if not os.path.exists(model_path):
        return None, None

    model  = joblib.load(model_path)
    scaler = joblib.load(scaler_path)
    return model, scaler
# Seuil minimum pour déclencher une alerte
MIN_ANOMALY_SCORE = 0.65

def detect_anomaly(app_name, current_metrics):
    """Détecte si les métriques actuelles sont anormales"""

    # Charger ou entraîner le modèle
    model, scaler = load_model(app_name)

    if model is None:
        model = train_model(app_name)
        if model is None:
            return False, 0.0, "Pas assez de données pour la détection"
        _, scaler = load_model(app_name)

    try:
        # Préparer les features
        features        = np.array(list(current_metrics.values())).reshape(1, -1)
        features_scaled = scaler.transform(features)

        # Prédiction : -1 = anomalie, 1 = normal
        prediction = model.predict(features_scaled)[0]

        # Score d'anomalie (plus négatif = plus anormal)
        score = model.score_samples(features_scaled)[0]

        # Normaliser le score entre 0 et 1
        anomaly_score = max(0.0, min(1.0, -score))

        is_anomaly = prediction == -1

        # ── Filtre seuil minimum ──────────────────────────────
        if is_anomaly and anomaly_score < MIN_ANOMALY_SCORE:
            print(f"  [{app_name}] Score {anomaly_score:.2f} < {MIN_ANOMALY_SCORE} → faux positif ignoré")
            is_anomaly = False

        if is_anomaly:
            reason = f"Score d'anomalie : {anomaly_score:.2f} — comportement inhabituel détecté"
        else:
            reason = f"Normal (score: {anomaly_score:.2f})"

        return is_anomaly, anomaly_score, reason

    except Exception as e:
        print(f"[DETECTOR] Erreur détection {app_name}: {str(e)}")
        return False, 0.0, str(e)
    
def process_collected_metrics(all_metrics):
    """Traite les métriques collectées et retourne les anomalies"""
    anomalies = []

    for app_name in ["keycloak", "postgresql", "mongodb", "redis", "redpanda"]:
        app_metrics = all_metrics.get(app_name, {})
        if not app_metrics:
            continue

        # Ajouter à l'historique
        add_to_history(app_name, app_metrics)

        # Détecter l'anomalie
        is_anomaly, score, reason = detect_anomaly(app_name, app_metrics)

        status = "🔴 ANOMALIE" if is_anomaly else "✅ Normal"
        print(f"  [{app_name}] {status} — {reason}")

        if is_anomaly:
            anomalies.append({
                "app":     app_name,
                "score":   score,
                "reason":  reason,
                "metrics": app_metrics,
            })

    return anomalies



