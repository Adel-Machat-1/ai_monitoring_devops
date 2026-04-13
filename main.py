from flask import Flask, request
import time
from config import (
    IGNORED_ALERTS, SKIP_SEVERITIES,
    DEDUP_WINDOW, MODELS, ALLOWED_ALERTS   # ← ALLOWED_ALERTS ajouté
)
from core.parser import parse_alert
from core.prometheus import get_prometheus_metrics
from core.loki import get_loki_logs
from core.kubernetes_events import get_kubernetes_events
from core.queue_worker import alert_queue
from core.gpt4 import current_model_index
from core.anomaly.scheduler import start_anomaly_scheduler
from datetime import datetime

app = Flask(__name__)
recent_alerts = {}

@app.route('/webhook/alert', methods=['POST'])
def receive_alert():
    print("\n" + "="*60)
    print("[ALERTE REÇUE]")
    print("="*60)

    alert_data = request.json
    alert_name = alert_data.get("groupLabels", {}).get("alertname", "")

    # ── FILTRE 1 : alertes système ignorées ───────────────────
    if alert_name in IGNORED_ALERTS:
        print(f"[SKIP] Système ignoré : {alert_name}")
        return {"status": "skipped"}

    parsed = parse_alert(alert_data)
    if not parsed:
        return {"status": "error"}, 400

    # ── FILTRE 2 : sévérité trop basse ────────────────────────
    if parsed['severity'] in SKIP_SEVERITIES:
        print(f"[SKIP] Sévérité : {parsed['severity']}")
        return {"status": "skipped"}

    # ── FILTRE 3 : seulement alertes de tes apps ──────────────
    if parsed['name'] not in ALLOWED_ALERTS:
        print(f"[SKIP] Hors scope : {parsed['name']}")
        return {"status": "skipped", "reason": "not_in_scope"}

    # ── FILTRE 4 : déduplication ──────────────────────────────
    alert_key = f"{parsed['name']}_{parsed['service']}"
    now       = time.time()
    if now - recent_alerts.get(alert_key, 0) < DEDUP_WINDOW:
        print(f"[SKIP] Doublon : {parsed['name']}")
        return {"status": "skipped"}

    recent_alerts[alert_key] = now
    print(f"[DEDUP] ✅ {alert_key}")
    print(f"  Alert    : {parsed['name']} | Severity : {parsed['severity']}")
    print(f"  Service  : {parsed['service']} | Pods : {parsed['affected_pods']}")

    # ── Prometheus ────────────────────────────────────────────
    first_pod = parsed['affected_pods'][0] if parsed['affected_pods'] else None
    metrics   = get_prometheus_metrics(job=parsed['job'], pod=first_pod)

    # ── Loki ──────────────────────────────────────────────────
    logs = get_loki_logs(
        service=parsed['service'],
        namespace=parsed['namespace']
    )

    # ── Events Kubernetes ─────────────────────────────────────
    print(f"\n[EVENTS] Récupération pour {first_pod or parsed['service']}...")
    events = get_kubernetes_events(
        pod=first_pod or parsed['service'],
        namespace=parsed['namespace']
    )

    # ── Queue ─────────────────────────────────────────────────
    queue_pos = alert_queue.qsize() + 1
    print(f"\n[QUEUE] Ajout : {parsed['name']} | Position : {queue_pos}")
    alert_queue.put((parsed, metrics, logs, events))

    print("\n[DONE] Alerte mise en queue → pipeline complet en cours...")
    print("="*60)
    return {"status": "queued"}

@app.route('/health', methods=['GET'])
def health():
    return {
        "status":     "ok",
        "timestamp":  datetime.now().isoformat(),
        "queue_size": alert_queue.qsize(),
        "model":      MODELS[current_model_index],
    }

if __name__ == "__main__":
    print("[DÉMARRAGE] http://localhost:5000")
    start_anomaly_scheduler(alert_queue)
    app.run(host="0.0.0.0", port=5000, debug=True)