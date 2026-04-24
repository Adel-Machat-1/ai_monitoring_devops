from flask import Flask, request, jsonify
import time
from config import (
    IGNORED_ALERTS, SKIP_SEVERITIES,
    DEDUP_WINDOW, MODELS, ALLOWED_ALERTS
)
from core.parser import parse_alert
from core.prometheus import get_prometheus_metrics
from core.loki import get_loki_logs
from core.kubernetes_events import get_kubernetes_events
from core.queue_worker import alert_queue
from core.gpt4 import current_model_index
from core.anomaly.scheduler import start_anomaly_scheduler
from core.state import pending_remediations          # ← AJOUT
from core.auto_remediation import execute_remediation # ← AJOUT
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

    if alert_name in IGNORED_ALERTS:
        print(f"[SKIP] Système ignoré : {alert_name}")
        return {"status": "skipped"}

    parsed = parse_alert(alert_data)
    if not parsed:
        return {"status": "error"}, 400

    if parsed['severity'] in SKIP_SEVERITIES:
        print(f"[SKIP] Sévérité : {parsed['severity']}")
        return {"status": "skipped"}

    if parsed['name'] not in ALLOWED_ALERTS:
        print(f"[SKIP] Hors scope : {parsed['name']}")
        return {"status": "skipped", "reason": "not_in_scope"}

    alert_key = f"{parsed['name']}_{parsed['service']}"
    now       = time.time()
    if now - recent_alerts.get(alert_key, 0) < DEDUP_WINDOW:
        print(f"[SKIP] Doublon : {parsed['name']}")
        return {"status": "skipped"}

    recent_alerts[alert_key] = now
    print(f"[DEDUP] ✅ {alert_key}")
    print(f"  Alert    : {parsed['name']} | Severity : {parsed['severity']}")
    print(f"  Service  : {parsed['service']} | Pods : {parsed['affected_pods']}")

    first_pod = parsed['affected_pods'][0] if parsed['affected_pods'] else None
    metrics   = get_prometheus_metrics(job=parsed['job'], pod=first_pod)
    logs      = get_loki_logs(service=parsed['service'], namespace=parsed['namespace'])

    print(f"\n[EVENTS] Récupération pour {first_pod or parsed['service']}...")
    events = get_kubernetes_events(
        pod=first_pod or parsed['service'],
        namespace=parsed['namespace']
    )

    queue_pos = alert_queue.qsize() + 1
    print(f"\n[QUEUE] Ajout : {parsed['name']} | Position : {queue_pos}")
    alert_queue.put((parsed, metrics, logs, events))

    print("\n[DONE] Alerte mise en queue → pipeline complet en cours...")
    print("="*60)
    return {"status": "queued"}

# ══════════════════════════════════════════════════════════════
# ROUTES SELF HEALING
# ══════════════════════════════════════════════════════════════
@app.route('/remediate/approve/<incident_id>', methods=['GET'])
def approve_remediation(incident_id):
    incident = pending_remediations.get(incident_id)
    if not incident:
        return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f0f2f5;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="padding:30px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0"
       style="background:white;border-radius:16px;overflow:hidden;
              box-shadow:0 8px 30px rgba(0,0,0,0.12);">
  <tr>
    <td style="background:linear-gradient(135deg,#1a1a2e,#0f3460);
               padding:28px;text-align:center;">
      <p style="font-size:38px;margin:0 0 6px;">🤖</p>
      <h1 style="color:white;margin:0;font-size:20px;letter-spacing:1px;">
        Agent IA — Kubernetes Monitoring
      </h1>
    </td>
  </tr>
  <tr>
    <td style="padding:40px;text-align:center;">
      <p style="font-size:48px;margin:0 0 16px;">❌</p>
      <h2 style="color:#1a202c;margin:0 0 8px;">Incident introuvable</h2>
      <p style="color:#718096;font-size:14px;">
        L'incident <b>{incident_id}</b> n'existe pas ou a déjà été traité.
      </p>
    </td>
  </tr>
  <tr>
    <td style="background:#2d3748;padding:18px 30px;text-align:center;">
      <p style="color:#a0aec0;margin:0;font-size:12px;">
        Agent IA Kubernetes — Monitoring automatisé
      </p>
    </td>
  </tr>
</table>
</td></tr>
</table>
</body>
</html>
        """, 404

    parsed   = incident['parsed']
    analysis = incident['analysis']

    print(f"\n[REMEDIATION] ✅ Approbation reçue pour {parsed['name']}")
    results = execute_remediation(analysis)
    del pending_remediations[incident_id]

    success_count = sum(1 for r in results if r['success'])
    total         = len(results)
    sev           = parsed['severity'].upper()
    emoji         = "🔴" if sev == "CRITICAL" else "🟠" if sev == "WARNING" else "🟡"
    color         = "#dc3545" if sev == "CRITICAL" else "#fd7e14" if sev == "WARNING" else "#ffc107"

    # ── Tableau des résultats ─────────────────────────────────
    rows = ""
    for r in results:
        if r.get('skipped'):
            status_icon = "⚠️"
            status_bg   = "#fffaf0"
        elif r['success']:
            status_icon = "✅"
            status_bg   = "#f0fff4"
        else:
            status_icon = "❌"
            status_bg   = "#fff5f5"

        rows += f"""
        <tr style="background:{status_bg};">
            <td style="padding:10px 16px;font-size:13px;text-align:center;
                       border-bottom:1px solid #e2e8f0;width:40px;">
                {status_icon}
            </td>
            <td style="padding:10px 16px;font-family:monospace;font-size:12px;
                       color:#2d3748;border-bottom:1px solid #e2e8f0;">
                {r['command']}
            </td>
            <td style="padding:10px 16px;font-size:11px;color:#718096;
                       border-bottom:1px solid #e2e8f0;max-width:200px;">
                {r['output'][:150] if r['output'] else '—'}
            </td>
        </tr>"""

    # ── Badge résultat ────────────────────────────────────────
    result_pct  = (success_count / total * 100) if total > 0 else 0
    result_color = "#38a169" if result_pct >= 75 else "#ed8936" if result_pct >= 50 else "#e53e3e"
    result_label = "Succès" if result_pct >= 75 else "Partiel" if result_pct >= 50 else "Échec"

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f0f2f5;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="padding:30px 0;">
<tr><td align="center">
<table width="650" cellpadding="0" cellspacing="0"
       style="background:white;border-radius:16px;overflow:hidden;
              box-shadow:0 8px 30px rgba(0,0,0,0.12);">

  <!-- HEADER -->
  <tr>
    <td style="background:linear-gradient(135deg,#1a1a2e,#0f3460);
               padding:28px;text-align:center;">
      <p style="font-size:38px;margin:0 0 6px;">🤖</p>
      <h1 style="color:white;margin:0;font-size:20px;letter-spacing:1px;">
        Agent IA — Kubernetes Monitoring
      </h1>
      <p style="color:#a0aec0;margin:6px 0 0;font-size:12px;">
        Auto-Remédiation Niveau 1 — Contrôle Humain
      </p>
    </td>
  </tr>

  <!-- BADGE STATUS -->
  <tr>
    <td style="background:#f0fff4;padding:18px;text-align:center;
               border-bottom:4px solid {result_color};">
      <span style="background:{result_color};color:white;padding:5px 20px;
                   border-radius:20px;font-size:13px;font-weight:bold;">
        ✅ Remédiation {result_label}
      </span>
      <h2 style="color:#1a202c;margin:12px 0 4px;font-size:20px;">
        {parsed['name']}
      </h2>
      <p style="color:#718096;margin:0;font-size:13px;">
        {success_count}/{total} commandes réussies
      </p>
    </td>
  </tr>

  <!-- CONTENU -->
  <tr>
    <td style="padding:24px 30px;">

      <!-- INFO INCIDENT -->

      <!-- TITRE TABLEAU -->
      <h3 style="color:#1a202c;font-size:15px;margin:0 0 12px;
                 border-left:4px solid {result_color};padding-left:12px;">
        🔧 Résultats des commandes kubectl
      </h3>

      <!-- TABLEAU COMMANDES -->
      <table width="100%" cellpadding="0" cellspacing="0"
             style="border:1px solid #e2e8f0;border-radius:10px;
                    overflow:hidden;margin-bottom:20px;">
        <thead>
          <tr style="background:#f0f4f8;">
            <th style="padding:10px 16px;font-size:12px;font-weight:700;
                       color:#4a5568;text-align:center;width:40px;">
              Status
            </th>
            <th style="padding:10px 16px;font-size:12px;font-weight:700;
                       color:#4a5568;text-align:left;">
              Commande
            </th>
            <th style="padding:10px 16px;font-size:12px;font-weight:700;
                       color:#4a5568;text-align:left;">
              Output
            </th>
          </tr>
        </thead>
        <tbody>
          {rows}
        </tbody>
      </table>

      <!-- RÉSUMÉ -->
      <div style="background:{'#f0fff4' if result_pct >= 75 else '#fffaf0'};
                  border:1px solid {'#c6f6d5' if result_pct >= 75 else '#fbd38d'};
                  border-radius:10px;padding:16px;text-align:center;">
        <p style="margin:0;color:{'#276749' if result_pct >= 75 else '#744210'};
                  font-size:14px;font-weight:bold;">
          📊 {success_count}/{total} commandes exécutées avec succès ({result_pct:.0f}%)
        </p>
        <p style="margin:6px 0 0;color:#718096;font-size:12px;">
          Exécuté le {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}
        </p>
      </div>

    </td>
  </tr>

  <!-- FOOTER -->
  <tr>
    <td style="background:#2d3748;padding:18px 30px;text-align:center;">
      <p style="color:#a0aec0;margin:0;font-size:12px;">
        Agent IA Kubernetes — Monitoring automatisé
      </p>
      <p style="color:#718096;margin:4px 0 0;font-size:11px;">
        Auto-Remédiation Niveau 1 — Contrôle humain via email
      </p>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>
    """


@app.route('/remediate/ignore/<incident_id>', methods=['GET'])
def ignore_remediation(incident_id):
    incident   = pending_remediations.pop(incident_id, None)
    alert_name = incident['parsed']['name'] if incident else incident_id

    print(f"[REMEDIATION] 🚫 Incident {incident_id} ignoré")

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f0f2f5;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="padding:30px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0"
       style="background:white;border-radius:16px;overflow:hidden;
              box-shadow:0 8px 30px rgba(0,0,0,0.12);">

  <!-- HEADER -->
  <tr>
    <td style="background:linear-gradient(135deg,#1a1a2e,#0f3460);
               padding:28px;text-align:center;">
      <p style="font-size:38px;margin:0 0 6px;">🤖</p>
      <h1 style="color:white;margin:0;font-size:20px;letter-spacing:1px;">
        Agent IA — Kubernetes Monitoring
      </h1>
      <p style="color:#a0aec0;margin:6px 0 0;font-size:12px;">
        Auto-Remédiation Niveau 1 — Contrôle Humain
      </p>
    </td>
  </tr>

  <!-- BADGE -->
  <tr>
    <td style="background:#fff5f5;padding:18px;text-align:center;
               border-bottom:4px solid #e53e3e;">
      <span style="background:#718096;color:white;padding:5px 20px;
                   border-radius:20px;font-size:13px;font-weight:bold;">
        🚫 Remédiation Ignorée
      </span>
      <h2 style="color:#1a202c;margin:12px 0 4px;font-size:20px;">
        {alert_name}
      </h2>
    </td>
  </tr>

  <!-- CONTENU -->
  <tr>
    <td style="padding:40px 30px;text-align:center;">
      <p style="font-size:48px;margin:0 0 16px;">🚫</p>
      <p style="color:#4a5568;font-size:14px;line-height:1.6;margin:0 0 20px;">
        L'incident <b>{alert_name}</b> a été ignoré.<br>
        Aucune action corrective n'a été exécutée.
      </p>
      <div style="background:#f7fafc;border-radius:10px;padding:16px;
                  border:1px solid #e2e8f0;">
        <p style="margin:0;color:#718096;font-size:12px;">
          Incident ID : <b style="font-family:monospace;">{incident_id}</b><br>
          Ignoré le {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}
        </p>
      </div>
    </td>
  </tr>

  <!-- FOOTER -->
  <tr>
    <td style="background:#2d3748;padding:18px 30px;text-align:center;">
      <p style="color:#a0aec0;margin:0;font-size:12px;">
        Agent IA Kubernetes — Monitoring automatisé
      </p>
      <p style="color:#718096;margin:4px 0 0;font-size:11px;">
        Auto-Remédiation Niveau 1 — Contrôle humain via email
      </p>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>
    """

@app.route('/health', methods=['GET'])
def health():
    return {
        "status"              : "ok",
        "timestamp"           : datetime.now().isoformat(),
        "queue_size"          : alert_queue.qsize(),
        "model"               : MODELS[current_model_index],
        "pending_remediations": len(pending_remediations),
    }

if __name__ == "__main__":
    print("[DÉMARRAGE] http://localhost:5000")
    start_anomaly_scheduler(alert_queue)
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        use_reloader=False
    )