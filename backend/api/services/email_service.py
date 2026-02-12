"""
Email service for sending dispute resolution communications via Gmail SMTP.
Used for demand notices, payment reminders, and legal notices.
"""

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)


def send_email(
    to_email: str,
    subject: str,
    body_html: str,
    cc_user: bool = False,
) -> Dict[str, Any]:
    """
    Send an email via Gmail SMTP.

    Args:
        to_email: Recipient email address.
        subject: Email subject line.
        body_html: HTML body of the email.
        cc_user: If True, CC the sender (GMAIL_ADDRESS) on the email.

    Returns:
        Dict with status, timestamp, and any error details.
    """
    gmail_address = os.getenv("GMAIL_ADDRESS")
    gmail_app_password = os.getenv("GMAIL_APP_PASSWORD")

    if not gmail_address or not gmail_app_password:
        logger.error("Gmail credentials not configured. Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD.")
        return {
            "status": "error",
            "error": "Email service not configured. Gmail credentials missing.",
            "timestamp": datetime.now().isoformat(),
        }

    msg = MIMEMultipart("alternative")
    msg["From"] = gmail_address
    msg["To"] = to_email
    msg["Subject"] = subject

    if cc_user:
        msg["Cc"] = gmail_address

    msg.attach(MIMEText(body_html, "html"))

    recipients = [to_email]
    if cc_user:
        recipients.append(gmail_address)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
            server.starttls()
            server.login(gmail_address, gmail_app_password)
            server.sendmail(gmail_address, recipients, msg.as_string())

        logger.info(f"Email sent to {to_email}: {subject}")
        return {
            "status": "sent",
            "to": to_email,
            "subject": subject,
            "timestamp": datetime.now().isoformat(),
        }

    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed. Check GMAIL_APP_PASSWORD.")
        return {
            "status": "error",
            "error": "Authentication failed. Check Gmail app password.",
            "timestamp": datetime.now().isoformat(),
        }
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error sending email: {e}")
        return {
            "status": "error",
            "error": f"SMTP error: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Unexpected error sending email: {e}")
        return {
            "status": "error",
            "error": f"Unexpected error: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }
