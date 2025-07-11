from typing import List

from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr
import smtplib

from ehp.config import settings
from ehp.utils.base import log_error


def send_mail(subject: str, body: str, recipients: List[str]) -> bool:
    """
    Sends a plain text email to a list of recipients.

    Args:
        subject: The subject of the email.
        body: The plain text body of the email.
        recipients: A list of recipient email addresses.

    Returns:
        True if the email was sent successfully, False otherwise.
    """
    if not all([subject, body, recipients]):
        log_error("Email subject, body, and recipients cannot be empty.")
        return False

    # Create the email message object
    msg = MIMEText(body, "plain", _charset="UTF-8")
    msg["Subject"] = subject

    # Set the "From" header with a friendly name
    msg["From"] = formataddr(
        (str(Header(settings.EMAIL_NAME, "utf-8")), settings.EMAIL_SENDER)
    )

    # Join the list of recipients into a single comma-separated string for the 'To' header
    msg["To"] = ", ".join(recipients)

    try:
        # Use a 'with' statement for automatic resource management (ensures s.quit() is called)
        with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as s:
            s.set_debuglevel(0)  # Set to 1 to see detailed SMTP logs
            s.starttls()  # Upgrade the connection to a secure one
            s.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)

            # The send_message method is modern and handles headers correctly.
            # The 'recipients' list is used for the SMTP envelope.
            s.send_message(msg, from_addr=settings.EMAIL_SENDER, to_addrs=recipients)

            log_error(f"Email sent successfully to: {', '.join(recipients)}")
            return True

    except smtplib.SMTPAuthenticationError as e:
        log_error(f"SMTP authentication error: Failed to log in. Check credentials. ({e})")
    except smtplib.SMTPConnectError as e:
        log_error(f"SMTP connection error: Failed to connect to the server. ({e})")
    except smtplib.SMTPRecipientsRefused as e:
        log_error(f"SMTP recipients refused: The server rejected the following recipients: {e}")
    except smtplib.SMTPException as e:
        log_error(f"An SMTP error occurred: {e}")
    except Exception as e:
        log_error(f"An unexpected error occurred while sending email: {e}")

    return False


def send_notification(subject: str, description: str, emails: List[str]) -> bool:
    try:
        result = send_mail(subject, description, emails)
    except Exception as e:
        log_error(e)
        return False
    else:
        return result
