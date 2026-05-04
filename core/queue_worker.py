import queue
import threading
import time
import uuid
from core.gpt4 import call_gpt4_with_retry, print_analysis
from reports.pdf_generator import generate_pdf_report
from reports.minio_uploader import upload_to_minio
from reports.email_sender import send_email_report
from core.state import pending_remediations

alert_queue = queue.Queue()
_processing = set()

def process_alert(parsed, metrics, logs, events):
    """Pipeline complet de traitement d'une alerte"""

    alert_key = f"{parsed['name']}_{parsed['service']}"
    if alert_key in _processing:
        print(f"[QUEUE] ⚠️ Déjà en cours : {alert_key} — ignoré")
        return None
    _processing.add(alert_key)

    try:
        # ── GPT-4 RCA ─────────────────────────────────────────
        analysis = call_gpt4_with_retry(parsed, metrics, logs, events)
        print_analysis(analysis, parsed)

        # ── Incident ID ───────────────────────────────────────
        incident_id = str(uuid.uuid4())[:8]  # ← DÉPLACÉ ICI EN PREMIER

        # ── Limiter les logs pour le PDF ──────────────────────
        try:
            if logs is None:
                logs_limited = []
            elif isinstance(logs, dict):
                streams = logs.get("data", {}).get("result", [])
                logs_limited = streams[:3] if streams else []
            elif isinstance(logs, list):
                logs_limited = logs[:3]
            elif isinstance(logs, str):
                logs_limited = [{"stream": {}, "values": [[0, logs[:500]]]}]
            else:
                logs_limited = []
        except:
            logs_limited = []

        # ── PDF avec incident_id dans le nom ──────────────────
        print("\n[PDF] Génération du rapport PDF...")
        pdf_bytes, filename = generate_pdf_report(
            parsed, metrics, logs_limited, analysis, events,
            incident_id=incident_id  # ← incident_id déjà défini ✅
        )

        if pdf_bytes:
            print(f"[PDF] ✅ PDF généré : {filename} ({len(pdf_bytes)} bytes)")
        else:
            filename  = f"incident_{incident_id}_{parsed['name']}.pdf"
            pdf_bytes = b""

        # ── MinIO ─────────────────────────────────────────────
        minio_url = upload_to_minio(pdf_bytes, filename)

        # ── Stocker dans pending_remediations ─────────────────
        pending_remediations[incident_id] = {
            "parsed"  : parsed,
            "analysis": analysis,
        }
        print(f"[REMEDIATION] 🔔 Incident {incident_id} en attente d'approbation")

        # ── Email avec boutons approbation ────────────────────
        send_email_report(parsed, analysis, pdf_bytes, filename, minio_url, incident_id)

        return analysis

    finally:
        _processing.discard(alert_key)


def queue_worker():
    """Worker qui traite les alertes dans la queue"""
    print("[QUEUE] Worker démarré")

    while True:
        try:
            job = alert_queue.get(timeout=1)
            if job is None:
                break

            parsed, metrics, logs, events = job
            print(f"\n[QUEUE] Traitement : {parsed['name']} ({parsed['severity']})")

            process_alert(parsed, metrics, logs, events)

            print(f"[QUEUE] ✅ Pipeline complet : {parsed['name']}")
            print(f"[QUEUE] Attente 30s...")
            time.sleep(30)

            alert_queue.task_done()

        except queue.Empty:
            continue
        except Exception as e:
            print(f"[QUEUE] Erreur: {str(e)}")
            alert_queue.task_done()


worker_thread = threading.Thread(target=queue_worker, daemon=True)
worker_thread.start()