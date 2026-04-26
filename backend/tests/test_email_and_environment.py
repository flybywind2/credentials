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


def test_environment_validation_rejects_removed_smtp_mode():
    settings = Settings(mail_mode="smtp")

    with pytest.raises(ValueError, match="MAIL_MODE"):
        validate_runtime_settings(settings)


@pytest.mark.parametrize("mode", ["ldap", "saml"])
def test_environment_validation_rejects_removed_sso_modes(mode):
    settings = Settings(sso_mode=mode)

    with pytest.raises(ValueError, match="SSO_MODE"):
        validate_runtime_settings(settings)


def test_approval_email_html_template_escapes_content():
    html = build_approval_email_html("승인 <요청>", "1단계 검토\n사유: <보완>")

    assert "&lt;요청&gt;" in html
    assert "1단계 검토" in html
    assert "&lt;보완&gt;" in html
    assert "<html" in html


def test_mail_api_email_service_posts_send_mail_payload(monkeypatch):
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
        mail_mode="mail_api",
        mail_api_base_url="mail.net",
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
    assert calls["headers"] == {}
    assert calls["data"] is None
    assert calls["json"] == {
        "recipients": ["group001@samsung.com"],
        "title": "승인 요청",
        "content": "<p>검토가 필요합니다.</p>",
    }
    assert calls["raised"] is True


def test_mail_api_email_service_uses_text_body_when_html_is_missing(monkeypatch):
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
        mail_mode="mail_api",
        mail_api_base_url="https://mail.net/send_mail",
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
    assert calls["json"] == {
        "recipients": ["group001@samsung.com"],
        "title": "승인 요청",
        "content": "검토가 필요합니다.",
    }
    assert calls["headers"] == {}
    assert calls["data"] is None
    assert calls["raised"] is True


def test_mail_api_mode_selects_mail_api_service(monkeypatch):
    monkeypatch.setattr(email_module, "settings", Settings(
        mail_mode="mail_api",
        mail_api_base_url="mail.net",
    ))

    assert isinstance(email_module.get_email_service(), email_module.MailApiEmailService)


def test_environment_validation_requires_mail_api_settings_when_enabled():
    settings = Settings(
        mail_mode="mail_api",
        mail_api_base_url="",
    )

    with pytest.raises(ValueError, match="MAIL_API_BASE_URL"):
        validate_runtime_settings(settings)


def test_environment_validation_requires_broker_employee_header_when_broker_enabled():
    settings = Settings(
        sso_mode="broker",
        broker_url="https://sso.example.com/svc0",
        service_url="https://example1.com",
        sso_broker_employee_header="",
    )

    with pytest.raises(ValueError, match="SSO_BROKER_EMPLOYEE_HEADER"):
        validate_runtime_settings(settings)


def test_environment_validation_requires_broker_urls_when_broker_enabled():
    settings = Settings(sso_mode="broker")

    with pytest.raises(ValueError, match="BROKER_URL"):
        validate_runtime_settings(settings)
