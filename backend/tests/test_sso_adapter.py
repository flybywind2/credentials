import pytest
from fastapi import HTTPException

from backend.services.sso import LdapSsoAdapter, MockSsoAdapter, SamlSsoAdapter, get_sso_adapter


def test_mock_sso_adapter_authenticates_seed_users():
    identity = MockSsoAdapter().authenticate("part001")

    assert identity.employee_id == "part001"
    assert identity.provider == "mock"


def test_ldap_sso_adapter_binds_and_returns_directory_identity():
    calls = []

    def fake_bind(employee_id, password, adapter):
        calls.append((employee_id, password, adapter.provider_url))
        return {"employee_id": employee_id, "displayName": "최파트장"}

    adapter = LdapSsoAdapter(
        provider_url="ldap://example.internal",
        bind_dn_template="{employee_id}@example.internal",
        ldap_bind_factory=fake_bind,
    )

    identity = adapter.authenticate("part001", password="secret")

    assert identity.employee_id == "part001"
    assert identity.provider == "ldap"
    assert identity.attributes["displayName"] == "최파트장"
    assert calls == [("part001", "secret", "ldap://example.internal")]


def test_ldap_sso_adapter_requires_password():
    adapter = LdapSsoAdapter(provider_url="ldap://example.internal")

    with pytest.raises(HTTPException) as exc_info:
        adapter.authenticate("part001", password=None)

    assert exc_info.value.status_code == 401


def test_saml_sso_adapter_validates_assertion_and_returns_identity():
    def fake_validator(saml_response, adapter):
        return {"employee_id": "group001", "displayName": "박그룹장", "raw": saml_response}

    adapter = SamlSsoAdapter(
        provider_url="https://idp.example.internal/saml",
        sp_entity_id="credential-app",
        acs_url="https://credential.example.com/api/auth/saml/acs",
        idp_entity_id="https://idp.example.internal",
        idp_sso_url="https://idp.example.internal/sso",
        idp_x509_cert="CERT",
        saml_response_validator=fake_validator,
    )

    identity = adapter.authenticate_response("encoded-assertion")

    assert identity.employee_id == "group001"
    assert identity.provider == "saml"
    assert identity.attributes["displayName"] == "박그룹장"


def test_directory_sso_adapter_requires_provider_url():
    adapter = LdapSsoAdapter(provider_url="")

    with pytest.raises(HTTPException) as exc_info:
        adapter.authenticate("part001", password="secret")

    assert exc_info.value.status_code == 500
    assert "SSO_PROVIDER_URL" in exc_info.value.detail


def test_get_sso_adapter_selects_mock_ldap_or_saml_adapter():
    assert isinstance(get_sso_adapter("mock"), MockSsoAdapter)
    assert isinstance(get_sso_adapter("ldap"), LdapSsoAdapter)
    assert isinstance(get_sso_adapter("saml"), SamlSsoAdapter)
