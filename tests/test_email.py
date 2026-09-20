from unittest.mock import MagicMock, patch

from src.accounts.email import send_email
from src.config.settings import settings


def test_send_email() -> None:
    smtp_instance = MagicMock()

    with patch(
        "src.accounts.email.smtplib.SMTP"
    ) as mocked_smtp:
        mocked_smtp.return_value.__enter__.return_value = (
            smtp_instance
        )

        send_email(
            recipient="user@example.com",
            subject="Test subject",
            body="Test body",
        )

    mocked_smtp.assert_called_once_with(
        settings.smtp_host,
        settings.smtp_port,
    )

    smtp_instance.send_message.assert_called_once()

    message = smtp_instance.send_message.call_args.args[0]

    assert message["From"] == settings.email_from
    assert message["To"] == "user@example.com"
    assert message["Subject"] == "Test subject"
    assert message.get_content().strip() == "Test body"
