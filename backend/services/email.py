from dataclasses import dataclass
import html
import json
import logging
from email.message import EmailMessage as SmtpMessage
from typing import Protocol
import smtplib

import httpx

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


class MailApiEmailService:
    def send(self, message: EmailMessage) -> dict:
        payload = self._payload(message)
        response = httpx.post(
            self._url(),
            **self._request_body(payload),
            headers=self._headers(),
            timeout=settings.mail_api_timeout_seconds,
        )
        response.raise_for_status()
        return {"status": "sent", "recipients": message.recipients}

    def _url(self) -> str:
        base_url = settings.mail_api_base_url.strip().rstrip("/")
        if not base_url.startswith(("http://", "https://")):
            base_url = f"https://{base_url}"
        if base_url.endswith("/send_mail"):
            return base_url
        return f"{base_url}/send_mail"

    def _payload(self, message: EmailMessage) -> dict:
        content_type = settings.mail_api_content_type or ("HTML" if message.html_body else "TEXT")
        contents = message.html_body if content_type.upper() == "HTML" and message.html_body else message.body
        return {
            "subject": message.subject,
            "contents": contents,
            "contentType": content_type,
            "docSecuType": settings.mail_api_doc_secu_type,
            "recipients": [
                {
                    "emailAddress": recipient,
                    "recipientType": settings.mail_api_recipient_type,
                }
                for recipient in message.recipients
            ],
        }

    def _headers(self) -> dict:
        if settings.mail_api_system_id:
            return {"System-ID": settings.mail_api_system_id}
        return {}

    def _request_body(self, payload: dict) -> dict:
        if settings.mail_api_payload_format.lower() == "form":
            return {
                "data": {
                    key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value
                    for key, value in payload.items()
                }
            }
        return {"json": payload}


def get_email_service() -> EmailService:
    mode = settings.smtp_mode.lower()
    if mode == "smtp":
        return SmtpEmailService()
    if mode == "mail_api":
        return MailApiEmailService()
    return DisabledEmailService()


def employee_email(employee_id: str | None) -> str | None:
    if not employee_id:
        return None
    return f"{employee_id}@samsung.com"


def build_approval_email_html(
    title: str,
    body: str,
    action_url: str | None = None,
    action_label: str = "바로가기",
) -> str:
    paragraphs = "".join(
        f"<p>{html.escape(line)}</p>" for line in body.splitlines() if line.strip()
    )
    action_button = ""
    if action_url:
        action_button = f"""
                <p style="margin-top:24px;">
                  <a href="{html.escape(action_url, quote=True)}" style="display:inline-block;background:#1f6feb;color:#ffffff;text-decoration:none;padding:10px 14px;border-radius:6px;font-weight:700;">
                    {html.escape(action_label)}
                  </a>
                </p>"""
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
{action_button}
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""
