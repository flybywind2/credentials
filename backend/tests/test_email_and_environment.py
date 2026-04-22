import pytest

from backend.config import Settings
from backend.services import email as email_module
from backend.services.email import DisabledEmailService, EmailMessage, build_approval_email_html
from backend.services.environment import validate_runtime_settings


def test_disabled_email_service_records_message_without_sending():
    service = DisabledEmailService()

    result = service.send(
        EmailMessage(
            subject="승인 요청",
            recipients=["approver@samsung.com"],
            body="검토가 필요합니다.",
        )
    )

    assert result["status"] == "disabled"
    assert service.sent_messages[0].subject == "승인 요청"


def test_environment_validation_requires_smtp_settings_when_enabled():
    settings = Settings(smtp_mode="smtp", smtp_host="", smtp_username="", smtp_password="")

    with pytest.raises(ValueError, match="SMTP_HOST"):
        validate_runtime_settings(settings)


def test_approval_email_html_template_escapes_content():
    html = build_approval_email_html("승인 <요청>", "1단계 검토\n사유: <보완>")

    assert "&lt;요청&gt;" in html
    assert "1단계 검토" in html
    assert "&lt;보완&gt;" in html
    assert "<html" in html


def test_mail_api_email_service_posts_json_payload(monkeypatch):
    calls = {}

    class Response:
        def raise_for_status(self):
            calls["raised"] = True

    def fake_post(url, *, json=None, data=None, headers=None, timeout=None):
        calls["url"] = url
        calls["json"] = json
        calls["data"] = data
        calls["headers"] = headers
        calls["timeout"] = timeout
        return Response()

    monkeypatch.setattr(email_module, "settings", Settings(
        smtp_mode="mail_api",
        mail_api_base_url="mail.net",
        mail_api_system_id="credential-system",
        mail_api_doc_secu_type="PERSONAL",
        mail_api_content_type="HTML",
        mail_api_payload_format="json",
        mail_api_timeout_seconds=7,
    ))
    monkeypatch.setattr(email_module.httpx, "post", fake_post)

    result = email_module.MailApiEmailService().send(
        EmailMessage(
            subject="승인 요청",
            recipients=["group001@samsung.com"],
            body="검토가 필요합니다.",
            html_body="<p>검토가 필요합니다.</p>",
        )
    )

    assert result == {"status": "sent", "recipients": ["group001@samsung.com"]}
    assert calls["url"] == "https://mail.net/send_mail"
    assert calls["timeout"] == 7
    assert calls["headers"] == {"System-ID": "credential-system"}
    assert calls["data"] is None
    assert calls["json"] == {
        "subject": "승인 요청",
        "contents": "<p>검토가 필요합니다.</p>",
        "contentType": "HTML",
        "docSecuType": "PERSONAL",
        "recipients": [
            {"emailAddress": "group001@samsung.com", "recipientType": "TO"}
        ],
    }
    assert calls["raised"] is True


def test_mail_api_email_service_posts_form_payload(monkeypatch):
    calls = {}

    class Response:
        def raise_for_status(self):
            calls["raised"] = True

    def fake_post(url, *, json=None, data=None, headers=None, timeout=None):
        calls["url"] = url
        calls["json"] = json
        calls["data"] = data
        calls["headers"] = headers
        calls["timeout"] = timeout
        return Response()

    monkeypatch.setattr(email_module, "settings", Settings(
        smtp_mode="mail_api",
        mail_api_base_url="https://mail.net/send_mail",
        mail_api_payload_format="form",
    ))
    monkeypatch.setattr(email_module.httpx, "post", fake_post)

    email_module.MailApiEmailService().send(
        EmailMessage(
            subject="승인 요청",
            recipients=["group001@samsung.com"],
            body="검토가 필요합니다.",
        )
    )

    assert calls["url"] == "https://mail.net/send_mail"
    assert calls["json"] is None
    assert calls["headers"] == {}
    assert calls["data"]["subject"] == "승인 요청"
    assert calls["data"]["contents"] == "검토가 필요합니다."
    assert '"emailAddress": "group001@samsung.com"' in calls["data"]["recipients"]
    assert calls["raised"] is True


def test_mail_api_mode_selects_mail_api_service(monkeypatch):
    monkeypatch.setattr(email_module, "settings", Settings(
        smtp_mode="mail_api",
        mail_api_base_url="mail.net",
    ))

    assert isinstance(email_module.get_email_service(), email_module.MailApiEmailService)


def test_environment_validation_requires_mail_api_settings_when_enabled():
    settings = Settings(
        smtp_mode="mail_api",
        mail_api_base_url="",
    )

    with pytest.raises(ValueError, match="MAIL_API_BASE_URL"):
        validate_runtime_settings(settings)
