import threading
import time
from datetime import datetime
from core.anomaly.collector import collect_all_metrics
from core.anomaly.detector import process_collected_metrics
from core.kubernetes_events import get_kubernetes_events   # ← AJOUT

INTERVAL = 300  

anomaly_dedup    = {}
ANOMALY_DEDUP_WINDOW = 1800 

SERVICE_MAPPING = {
    "keycloak":   "keycloak-0",
    "postgresql": "postgresql-primary-0",
    "mongodb":    "mongodb-0",
    "redis":      "redis-master-0",
    "redpanda":   "redpanda-0",
}

def create_anomaly_alert(app_name, anomaly_info):
    service = SERVICE_MAPPING.get(app_name, app_name)
    return {
        "name":           f"AnomalyDetected_{app_name.capitalize()}",
        "service":        service,
        "job":            f"{app_name}-metrics",
        "namespace":      "apps",
        "severity":       "warning",
        "status":         "firing",
        "description":    f"Anomalie ML détectée sur {app_name} — {anomaly_info['reason']}",
        "summary":        f"Comportement anormal détecté sur {app_name}",
        "started_at":     datetime.now().isoformat(),
        "affected_pods":  [service],
        "firing_count":   1,
        "resolved_count": 0,
        "total_alerts":   1,
        "source":         "anomaly_detection",
        "anomaly_score":  anomaly_info['score'],
        "raw_metrics":    anomaly_info['metrics'],
    }

def run_anomaly_detection(alert_queue):
    print(f"[SCHEDULER] Démarrage — intervalle: {INTERVAL//60} minutes")
    print(f"[SCHEDULER] Première collecte dans 30 secondes...")
    time.sleep(30)

    while True:
        try:
            print(f"\n{'='*50}")
            print(f"[SCHEDULER] Cycle — {datetime.now().strftime('%H:%M:%S')}")
            print(f"{'='*50}")

            all_metrics = collect_all_metrics()
            anomalies   = process_collected_metrics(all_metrics)

            if anomalies:
                print(f"\n[SCHEDULER] ⚠️ {len(anomalies)} anomalie(s) détectée(s) !")

                for anomaly in anomalies:
                    app_name = anomaly['app']
                    now      = time.time()

                    # ── Déduplication anomalie ML ─────────────
                    last_sent = anomaly_dedup.get(app_name, 0)
                    if now - last_sent < ANOMALY_DEDUP_WINDOW:
                        remaining = int((ANOMALY_DEDUP_WINDOW - (now - last_sent)) / 60)
                        print(f"[SCHEDULER] [SKIP] {app_name} déjà alerté — prochain dans {remaining} min")
                        continue

                    # ── Marquer comme envoyé ──────────────────
                    anomaly_dedup[app_name] = now

                    from core.prometheus import get_prometheus_metrics
                    from core.loki import get_loki_logs

                    parsed  = create_anomaly_alert(app_name, anomaly)
                    service = SERVICE_MAPPING.get(app_name, app_name)

                    metrics = get_prometheus_metrics(
                        job=f"{app_name}-metrics",
                        pod=service
                    )

                    minutes = 60 if app_name == "redis" else 10
                    logs    = get_loki_logs(
                        service=service,
                        namespace="apps",
                        minutes=minutes
                    )

                    events = get_kubernetes_events(
                        pod=service,
                        namespace="apps"
                    )

                    print(f"[SCHEDULER] → Envoi dans queue GPT-4 : {parsed['name']}")
                    alert_queue.put((parsed, metrics, logs, events))
            else:
                print(f"\n[SCHEDULER] ✅ Tout est normal")

        except Exception as e:
            print(f"[SCHEDULER] ❌ Erreur: {str(e)}")

        print(f"\n[SCHEDULER] Prochain cycle dans {INTERVAL//60} minutes...")
        time.sleep(INTERVAL)

def start_anomaly_scheduler(alert_queue):
    thread = threading.Thread(
        target=run_anomaly_detection,
        args=(alert_queue,),
        daemon=True
    )
    thread.start()
    print(f"[SCHEDULER] Thread démarré ✅")
    return thread