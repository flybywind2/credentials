from dataclasses import dataclass
import html
import logging
from email.message import EmailMessage as SmtpMessage
from typing import Protocol
import smtplib

from backend.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailMessage:
    subject: str
    recipients: list[str]
    body: str
    html_body: str | None = None


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
        if message.html_body:
            smtp_message.add_alternative(message.html_body, subtype="html")
        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as client:
                client.starttls()
                if settings.smtp_username:
                    client.login(settings.smtp_username, settings.smtp_password)
                client.send_message(smtp_message)
            return {"status": "sent", "recipients": message.recipients}
        except Exception:
            logger.exception(
                "smtp email send failed subject=%s recipients=%s",
                message.subject,
                ",".join(message.recipients),
            )
            raise


def get_email_service() -> EmailService:
    if settings.smtp_mode.lower() == "smtp":
        return SmtpEmailService()
    return DisabledEmailService()


def employee_email(employee_id: str | None) -> str | None:
    if not employee_id:
        return None
    return f"{employee_id}@samsung.com"


def build_approval_email_html(title: str, body: str) -> str:
    paragraphs = "".join(
        f"<p>{html.escape(line)}</p>" for line in body.splitlines() if line.strip()
    )
    return f"""<!doctype html>
<html lang="ko">
  <head>
    <meta charset="utf-8">
    <title>{html.escape(title)}</title>
  </head>
  <body style="margin:0;background:#f6f7f9;color:#20242a;font-family:Arial,'Malgun Gothic',sans-serif;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f6f7f9;padding:24px;">
      <tr>
        <td align="center">
          <table role="presentation" width="640" cellspacing="0" cellpadding="0" style="background:#ffffff;border:1px solid #d9dde3;border-radius:8px;">
            <tr>
              <td style="padding:20px 24px;border-bottom:1px solid #d9dde3;">
                <h1 style="margin:0;font-size:20px;">{html.escape(title)}</h1>
              </td>
            </tr>
            <tr>
              <td style="padding:20px 24px;font-size:14px;line-height:1.6;">
                {paragraphs or "<p>기밀분류시스템 알림입니다.</p>"}
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""
