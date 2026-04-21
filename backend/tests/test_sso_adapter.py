import pytest
from fastapi import HTTPException

from backend.services.sso import LdapSsoAdapter, MockSsoAdapter, SamlSsoAdapter, get_sso_adapter


def test_mock_sso_adapter_authenticates_seed_users():
    user = MockSsoAdapter().authenticate("part001")

    assert user["role"] == "INPUTTER"
    assert user["email"] == "part001@samsung.com"


def test_ldap_sso_adapter_authenticates_directory_user():
    adapter = LdapSsoAdapter(provider_url="ldap://example.internal")

    user = adapter.authenticate("part001")

    assert user["role"] == "INPUTTER"
    assert user["sso_provider"] == "ldap"


def test_saml_sso_adapter_authenticates_directory_user():
    adapter = SamlSsoAdapter(provider_url="https://idp.example.internal/saml")

    user = adapter.authenticate("group001")

    assert user["role"] == "APPROVER"
    assert user["sso_provider"] == "saml"


def test_directory_sso_adapter_requires_provider_url():
    adapter = LdapSsoAdapter(provider_url="")

    with pytest.raises(HTTPException) as exc_info:
        adapter.authenticate("part001")

    assert exc_info.value.status_code == 500
    assert "SSO_PROVIDER_URL" in exc_info.value.detail


def test_get_sso_adapter_selects_mock_ldap_or_saml_adapter():
    assert isinstance(get_sso_adapter("mock"), MockSsoAdapter)
    assert isinstance(get_sso_adapter("ldap"), LdapSsoAdapter)
    assert isinstance(get_sso_adapter("saml"), SamlSsoAdapter)
