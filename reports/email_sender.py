import smtplib
import ssl
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from config import (
    GMAIL_HOST, GMAIL_PORT,
    GMAIL_USERNAME, GMAIL_PASSWORD,
    EMAIL_FROM, EMAIL_TO
)

def send_email_report(parsed, analysis, pdf_bytes, filename, minio_url):
    print(f"\n[EMAIL] Envoi du rapport pour {parsed['name']}...")

    sev     = parsed['severity'].upper()
    emoji   = "🔴" if sev == "CRITICAL" else "🟠" if sev == "WARNING" else "🟡"
    actions = analysis.get('actions_correctives', []) if "error" not in analysis else []
    cmds    = analysis.get('commandes_diagnostic', []) if "error" not in analysis else []
    color   = "#dc3545" if sev == "CRITICAL" else "#fd7e14" if sev == "WARNING" else "#ffc107"

    # ── Version HTML (même contenu, beau style) ───────────────
    actions_html = "".join([
        f'<tr style="background:{"#f8f9fa" if i%2==0 else "white"};">'
        f'<td style="padding:10px 16px;font-size:13px;color:#2d3748;border-bottom:1px solid #e2e8f0;">'
        f'<span style="background:{color};color:white;border-radius:50%;padding:2px 7px;'
        f'font-size:11px;margin-right:8px;">{i}</span>{a}</td></tr>'
        for i, a in enumerate(actions, 1)
    ])

    cmds_html = "".join([
        f'<tr><td style="padding:8px 16px;font-family:monospace;font-size:12px;'
        f'color:#00ff41;background:#1a1a1a;border-bottom:1px solid #333;">'
        f'<span style="color:#888;">$ </span>{c}</td></tr>'
        for c in cmds
    ])

    html_body = f"""
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
        Root Cause Analysis Automatisé
      </p>
    </td>
  </tr>

  <!-- BADGE -->
  <tr>
    <td style="background:{"#fff5f5" if sev=="CRITICAL" else "#fff8f0"};
               padding:18px;text-align:center;border-bottom:4px solid {color};">
      <span style="background:{color};color:white;padding:5px 20px;
                   border-radius:20px;font-size:13px;font-weight:bold;">
        {emoji} {sev}
      </span>
      <h2 style="color:#1a202c;margin:12px 0 4px;font-size:20px;">
        {parsed['name']}
      </h2>
    </td>
  </tr>

  <!-- CONTENU PRINCIPAL -->
  <tr>
    <td style="padding:24px 30px;">

      <!-- Bonjour -->
      <p style="color:#2d3748;font-size:14px;margin:0 0 20px;">
        Bonjour,<br><br>
        Un incident a été détecté sur votre cluster Kubernetes.
      </p>

      <!-- INCIDENT -->
      <div style="background:#f7fafc;border-radius:10px;padding:20px;
                  border-left:4px solid {color};margin-bottom:20px;">
        <table width="100%" cellpadding="0" cellspacing="0">
          <tr>
            <td style="font-weight:600;color:#4a5568;font-size:13px;
                       padding:5px 0;width:130px;">Alerte</td>
            <td style="color:#2d3748;font-size:13px;padding:5px 0;">
              {parsed['name']}
            </td>
          </tr>
          <tr>
            <td style="font-weight:600;color:#4a5568;font-size:13px;padding:5px 0;">
              Service
            </td>
            <td style="color:#2d3748;font-size:13px;padding:5px 0;">
              {parsed['service']}
            </td>
          </tr>
          <tr>
            <td style="font-weight:600;color:#4a5568;font-size:13px;padding:5px 0;">
              Namespace
            </td>
            <td style="color:#2d3748;font-size:13px;padding:5px 0;">
              {parsed['namespace']}
            </td>
          </tr>
          <tr>
            <td style="font-weight:600;color:#4a5568;font-size:13px;padding:5px 0;">
              Sévérité
            </td>
            <td style="padding:5px 0;">
              <span style="background:{color};color:white;padding:2px 10px;
                           border-radius:10px;font-size:12px;">{sev}</span>
            </td>
          </tr>
          <tr>
            <td style="font-weight:600;color:#4a5568;font-size:13px;padding:5px 0;">
              Pods
            </td>
            <td style="color:#2d3748;font-size:13px;padding:5px 0;">
              {', '.join(parsed['affected_pods']) if parsed['affected_pods'] else 'N/A'}
            </td>
          </tr>
          <tr>
            <td style="font-weight:600;color:#4a5568;font-size:13px;padding:5px 0;">
              Démarré le
            </td>
            <td style="color:#2d3748;font-size:13px;padding:5px 0;">
              {parsed['started_at'][:19].replace('T', ' ')}
            </td>
          </tr>
        </table>
      </div>

      <!-- ANALYSE RCA -->
      <h3 style="color:#1a202c;font-size:15px;margin:0 0 12px;
                 border-left:4px solid #e53e3e;padding-left:12px;">
        🔍 Anomalie détectée
      </h3>
      <div style="background:#fff5f5;border:1px solid #fed7d7;border-radius:10px;
                  padding:16px;color:#2d3748;font-size:13px;line-height:1.7;
                  margin-bottom:20px;">
        {analysis.get('anomalie', 'N/A')}
      </div>

     
      <!-- PDF -->
      <div style="background:#ebf8ff;border:1px solid #bee3f8;border-radius:10px;
                  padding:14px;text-align:center;margin-bottom:20px;">
        <p style="margin:0;color:#2b6cb0;font-size:13px;font-weight:600;">
          📄 Rapport PDF complet disponible en pièce jointe
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
        Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}
      </p>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>
"""

    try:
        msg            = MIMEMultipart('alternative')
        msg['From']    = EMAIL_FROM
        msg['To']      = EMAIL_TO
        msg['Subject'] = f"{emoji} [{sev}] {parsed['name']} — Rapport RCA Kubernetes"

      
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))

        # ── Pièce jointe PDF ──────────────────────────────────
        final_msg            = MIMEMultipart('mixed')
        final_msg['From']    = EMAIL_FROM
        final_msg['To']      = EMAIL_TO
        final_msg['Subject'] = msg['Subject']

        for part in msg.get_payload():
            final_msg.attach(part)

        pdf_part = MIMEBase('application', 'octet-stream')
        pdf_part.set_payload(pdf_bytes)
        encoders.encode_base64(pdf_part)
        pdf_part.add_header(
            'Content-Disposition',
            f'attachment; filename="{filename}"'
        )
        final_msg.attach(pdf_part)

        # ── Gmail SMTP ────────────────────────────────────────
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode    = ssl.CERT_NONE

        with smtplib.SMTP(GMAIL_HOST, GMAIL_PORT, timeout=30) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(GMAIL_USERNAME, GMAIL_PASSWORD)
            server.sendmail(EMAIL_FROM, EMAIL_TO, final_msg.as_string())

        print(f"[EMAIL] ✅ Email envoyé à {EMAIL_TO}")
        time.sleep(2)
        return True

    except Exception as e:
        print(f"[EMAIL] ❌ Erreur : {str(e)}")
        return False