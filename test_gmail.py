import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

HOST     = "smtp.gmail.com"
PORT     = 587
USERNAME = "adelmachat9@gmail.com"
PASSWORD = "ewqxxomdayfozyqh"
TO       = "adelmachat92@gmail.com"  # ← email où tu veux recevoir

try:
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    msg            = MIMEMultipart()
    msg['From']    = USERNAME
    msg['To']      = TO
    msg['Subject'] = "🤖 Test Agent IA Kubernetes"

    body = "Bonjour ! Ceci est un test de l'Agent IA Kubernetes."
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    with smtplib.SMTP(HOST, PORT, timeout=10) as server:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(USERNAME, PASSWORD)
        server.sendmail(USERNAME, TO, msg.as_string())
        print(f"✅ Email envoyé à {TO} !")

except Exception as e:
    print(f"❌ Erreur : {str(e)}")