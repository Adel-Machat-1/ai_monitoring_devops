import queue
import threading
import time
from core.gpt4 import call_gpt4_with_retry, print_analysis
from reports.pdf_generator import generate_pdf_report
from reports.minio_uploader import upload_to_minio
from reports.email_sender import send_email_report

alert_queue = queue.Queue()

def queue_worker():
    print("[QUEUE] Worker démarré")
    while True:
        try:
            job = alert_queue.get(timeout=1)
            if job is None:
                break

            # ── Unpack avec events ────────────────────────────
            parsed, metrics, logs, events = job

            print(f"\n[QUEUE] Traitement : {parsed['name']} ({parsed['severity']})")

            analysis         = call_gpt4_with_retry(parsed, metrics, logs, events)
            print_analysis(analysis, parsed)
            pdf_bytes, fname = generate_pdf_report(parsed, metrics, logs, analysis, events)
            minio_url        = upload_to_minio(pdf_bytes, fname)
            send_email_report(parsed, analysis, pdf_bytes, fname, minio_url)

            alert_queue.task_done()
            print(f"[QUEUE] ✅ Pipeline complet : {parsed['name']}")
            print(f"[QUEUE] Attente 30s...")
            time.sleep(30)

        except queue.Empty:
            continue
        except Exception as e:
            print(f"[QUEUE] Erreur: {str(e)}")
            alert_queue.task_done()

worker_thread = threading.Thread(target=queue_worker, daemon=True)
worker_thread.start()