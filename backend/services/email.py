from dataclasses import dataclass
import html
from typing import Protocol

import httpx

from backend.config import settings


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


class MailApiEmailService:
    def send(self, message: EmailMessage) -> dict:
        payload = self._payload(message)
        response = httpx.post(
            self._url(),
            json=payload,
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
        content = message.html_body if message.html_body else message.body
        return {
            "recipients": message.recipients,
            "title": message.subject,
            "content": content,
        }

    def _headers(self) -> dict:
        if settings.mail_api_system_id:
            return {"System-ID": settings.mail_api_system_id}
        return {}


def get_email_service() -> EmailService:
    mode = settings.mail_mode.lower()
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
