import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from config import (
    MAILTRAP_HOST, MAILTRAP_PORT,
    MAILTRAP_USERNAME, MAILTRAP_PASSWORD,
    EMAIL_FROM, EMAIL_TO
)

def send_email_report(parsed, analysis, pdf_bytes, filename, minio_url):
    print(f"\n[EMAIL] Envoi du rapport pour {parsed['name']}...")

    sev     = parsed['severity'].upper()
    emoji   = "🔴" if sev == "CRITICAL" else "🟠" if sev == "WARNING" else "🟡"
    actions = analysis.get('actions_correctives', []) if "error" not in analysis else []

    body = f"""Bonjour,

Un incident a été détecté sur votre cluster Kubernetes.

{'='*55}
{emoji} INCIDENT — {sev}
{'='*55}

Alerte      : {parsed['name']}
Service     : {parsed['service']}
Namespace   : {parsed['namespace']}
Sévérité    : {sev}
Pods        : {', '.join(parsed['affected_pods']) if parsed['affected_pods'] else 'N/A'}
Démarré le  : {parsed['started_at'][:19].replace('T', ' ')}

{'='*55}
ANALYSE ROOT CAUSE ANALYSIS
{'='*55}

Anomalie    : {analysis.get('anomalie', 'N/A')}
Cause Root  : {analysis.get('cause_probable', 'N/A')}

Actions correctives :
{chr(10).join(f"  {i+1}. {a}" for i, a in enumerate(actions))}

Prévention  : {analysis.get('prevention', 'N/A')}

{'='*55}
Rapport PDF : {minio_url or 'N/A'}
{'='*55}

--
Agent IA Kubernetes
Généré le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    try:
        msg            = MIMEMultipart()
        msg['From']    = EMAIL_FROM
        msg['To']      = EMAIL_TO
        msg['Subject'] = f"{emoji} [{sev}] {parsed['name']} — Rapport RCA Kubernetes"

        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        # Pièce jointe PDF
        attachment = MIMEBase('application', 'octet-stream')
        attachment.set_payload(pdf_bytes)
        encoders.encode_base64(attachment)
        attachment.add_header(
            'Content-Disposition',
            f'attachment; filename="{filename}"'
        )
        msg.attach(attachment)

        # ── Fix SSL — contexte sans vérification ─────────────
        context = ssl.create_default_context()
        context.check_hostname = False        # ← désactive hostname check
        context.verify_mode    = ssl.CERT_NONE  # ← désactive cert verify

        with smtplib.SMTP(MAILTRAP_HOST, MAILTRAP_PORT, timeout=30) as server:
            server.ehlo()
            server.starttls(context=context)  # ← contexte SSL personnalisé
            server.ehlo()
            server.login(MAILTRAP_USERNAME, MAILTRAP_PASSWORD)
            server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())

        print(f"[EMAIL] ✅ Email envoyé à {EMAIL_TO}")
        return True

    except Exception as e:
        print(f"[EMAIL] ❌ Erreur : {str(e)}")
        return False