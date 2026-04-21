import pytest

from backend.config import Settings
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
