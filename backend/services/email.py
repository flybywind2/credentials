from dataclasses import dataclass
from email.message import EmailMessage as SmtpMessage
from typing import Protocol
import smtplib

from backend.config import settings


@dataclass(frozen=True)
class EmailMessage:
    subject: str
    recipients: list[str]
    body: str


class EmailService(Protocol):
    def send(self, message: EmailMessage) -> dict:
        ...


class DisabledEmailService:
    def __init__(self) -> None:
        self.sent_messages: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> dict:
        self.sent_messages.append(message)
        return {"status": "disabled", "recipients": message.recipients}


class SmtpEmailService:
    def send(self, message: EmailMessage) -> dict:
        smtp_message = SmtpMessage()
        smtp_message["Subject"] = message.subject
        smtp_message["From"] = settings.smtp_username
        smtp_message["To"] = ", ".join(message.recipients)
        smtp_message.set_content(message.body)
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as client:
            client.starttls()
            if settings.smtp_username:
                client.login(settings.smtp_username, settings.smtp_password)
            client.send_message(smtp_message)
        return {"status": "sent", "recipients": message.recipients}


def get_email_service() -> EmailService:
    if settings.smtp_mode.lower() == "smtp":
        return SmtpEmailService()
    return DisabledEmailService()


def employee_email(employee_id: str | None) -> str | None:
    if not employee_id:
        return None
    return f"{employee_id}@samsung.com"
