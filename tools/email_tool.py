import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config.settings import SMTP_EMAIL, SMTP_PASSWORD

logger = logging.getLogger(__name__)

def send_email(to_email: str, subject: str, body: str) -> tuple[bool, str | None]:
    """
    Send an email using SMTP (e.g. Gmail App Passwords).
    Returns (success, error_message).
    """
    # If no SMTP credentials are provided, run in Mock/Development Mode
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        logger.warning("SMTP_EMAIL or SMTP_PASSWORD not configured. Running in Mock/Development Mode!")
        logger.info(f"[MOCK EMAIL SENT]\nTo: {to_email}\nSubject: {subject}\nBody:\n{body}\n---")
        return True, None

    logger.info(f"Sending email to {to_email} via SMTP...")
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = SMTP_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect to Gmail SMTP Server (port 587 for STARTTLS)
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        
        # Login
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        
        # Send
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Email successfully sent to {to_email}.")
        return True, None
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to send email to {to_email}: {error_msg}")
        return False, error_msg
