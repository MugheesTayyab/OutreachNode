import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config.settings import SMTP_EMAIL, SMTP_PASSWORD

logger = logging.getLogger(__name__)

def _get_smtp_config():
    from middleware.state_manager import StateManager
    saved = StateManager.load_settings()
    return {
        "host": saved.get("smtp_host") or "smtp.gmail.com",
        "port": int(saved.get("smtp_port") or 587),
        "user": saved.get("smtp_user") or SMTP_EMAIL,
        "pass": saved.get("smtp_pass") or SMTP_PASSWORD,
        "from_name": saved.get("smtp_from_name") or "",
        "unsubscribe_email": saved.get("unsubscribe_email") or "",
    }

def send_email(to_email: str, subject: str, body: str, campaign_id: str = None) -> tuple[bool, str | None]:
    cfg = _get_smtp_config()

    if not cfg["user"] or not cfg["pass"]:
        logger.warning("SMTP not configured. Running in Mock/Development Mode!")
        logger.info(f"[MOCK EMAIL SENT]\nTo: {to_email}\nSubject: {subject}\nBody:\n{body}\n---")
        return True, None

    from middleware.state_manager import StateManager
    if StateManager.is_suppressed(to_email):
        logger.warning(f"Email {to_email} is suppressed. Skipping.")
        return False, "Recipient has unsubscribed"

    unsubscribe_url = f"http://127.0.0.1:5000/unsubscribe?email={to_email}"
    footer = f"\n\n---\nTo stop receiving emails, unsubscribe here: {unsubscribe_url}"
    full_body = body + footer

    logger.info(f"Sending email to {to_email} via SMTP ({cfg['host']}:{cfg['port']})...")
    try:
        msg = MIMEMultipart()
        sender = f"{cfg['from_name']} <{cfg['user']}>" if cfg["from_name"] else cfg["user"]
        msg['From'] = sender
        msg['To'] = to_email
        msg['Subject'] = subject
        if cfg["unsubscribe_email"]:
            msg['List-Unsubscribe'] = f'<mailto:{cfg["unsubscribe_email"]}?subject=unsubscribe>'
        msg.attach(MIMEText(full_body, 'plain'))

        server = smtplib.SMTP(cfg["host"], cfg["port"])
        server.starttls()
        server.login(cfg["user"], cfg["pass"])
        server.send_message(msg)
        server.quit()

        logger.info(f"Email successfully sent to {to_email}.")
        return True, None
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to send email to {to_email}: {error_msg}")
        return False, error_msg
