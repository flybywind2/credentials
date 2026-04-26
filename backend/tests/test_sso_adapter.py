import pytest
from fastapi import HTTPException

from backend.services.sso import BrokerSsoAdapter, MockSsoAdapter, get_sso_adapter


def test_mock_sso_adapter_authenticates_seed_users():
    identity = MockSsoAdapter().authenticate("part001")

    assert identity.employee_id == "part001"
    assert identity.provider == "mock"


def test_get_sso_adapter_selects_only_mock_or_broker_adapter():
    assert isinstance(get_sso_adapter("mock"), MockSsoAdapter)
    assert isinstance(get_sso_adapter("broker"), BrokerSsoAdapter)


@pytest.mark.parametrize("mode", ["ldap", "saml"])
def test_get_sso_adapter_rejects_removed_sso_modes(mode):
    with pytest.raises(HTTPException) as exc_info:
        get_sso_adapter(mode)

    assert exc_info.value.status_code == 500
    assert "Unsupported SSO_MODE" in exc_info.value.detail


def test_broker_sso_adapter_rejects_form_login():
    adapter = BrokerSsoAdapter()

    with pytest.raises(HTTPException) as exc_info:
        adapter.authenticate("part001")

    assert exc_info.value.status_code == 400
    assert "broker header" in exc_info.value.detail
