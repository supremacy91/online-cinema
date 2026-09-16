import smtplib
from email.message import EmailMessage

from src.config.settings import settings


def send_email(
    recipient: str,
    subject: str,
    body: str,
) -> None:
    message = EmailMessage()

    message["From"] = settings.email_from
    message["To"] = recipient
    message["Subject"] = subject

    message.set_content(body)

    with smtplib.SMTP(
        settings.smtp_host,
        settings.smtp_port,
    ) as smtp:
        smtp.send_message(message)
