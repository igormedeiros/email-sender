
import smtplib
import os
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from dotenv import load_dotenv

# Config logging
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

def test_smtp_debug():
    load_dotenv()
    
    # SMTP details from .env
    host = os.getenv("SMTP_HOST_OVERRIDE", "smtplw.com.br")
    port = int(os.getenv("SMTP_PORT", 587))
    user = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    
    # Sender and recipient
    # Try a sender that we know might work or use the same as the config
    from_email = "mkt@envio.treineinsite.com.br"
    to_email = "igor.medeiros@gmail.com"
    
    print(f"Connecting to {host}:{port}...")
    
    try:
        smtp = smtplib.SMTP(host, port, timeout=10)
        smtp.set_debuglevel(1)  # ENABLE FULL DEBUG OUTPUT
        
        smtp.starttls()
        print("Logging in...")
        smtp.login(user, password)
        
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "DEBUG: TESTE DE ENVIO - Treineinsite (PE)"
        msg["From"] = f"Treineinsite <{from_email}>"
        msg["To"] = to_email
        
        body = "Este é um teste de debug para verificar os códigos de resposta do SMTP Locaweb."
        msg.attach(MIMEText(body, "plain"))
        
        print(f"Sending to {to_email} from {from_email}...")
        smtp.send_message(msg)
        print("Success message sent (from smtplib perspective)")
        
        smtp.quit()
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    test_smtp_debug()
