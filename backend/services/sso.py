from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol
from urllib.parse import urlparse

from fastapi import HTTPException

from backend.config import settings
from backend.services.auth_service import get_mock_user


@dataclass(frozen=True)
class AuthenticatedIdentity:
    employee_id: str
    provider: str
    attributes: dict[str, Any] = field(default_factory=dict)


class SsoAdapter(Protocol):
    def authenticate(self, employee_id: str, password: str | None = None) -> AuthenticatedIdentity:
        pass


def _first_value(value: Any) -> Any:
    if isinstance(value, list | tuple):
        return value[0] if value else None
    return value


@dataclass(frozen=True)
class MockSsoAdapter:
    provider: str = "mock"

    def authenticate(self, employee_id: str, password: str | None = None) -> AuthenticatedIdentity:
        user = get_mock_user(employee_id)
        attributes = {"name": user["name"], "email": user["email"]} if user else {}
        return AuthenticatedIdentity(
            employee_id=employee_id,
            provider=self.provider,
            attributes=attributes,
        )


@dataclass(frozen=True)
class BrokerSsoAdapter:
    provider: str = "broker"

    def authenticate(self, employee_id: str, password: str | None = None) -> AuthenticatedIdentity:
        raise HTTPException(
            status_code=400,
            detail="Broker SSO uses the configured broker header instead of form login",
        )


@dataclass(frozen=True)
class LdapSsoAdapter:
    provider_url: str
    provider: str = "ldap"
    bind_dn_template: str = "{employee_id}"
    search_base: str = ""
    search_filter: str = "(sAMAccountName={employee_id})"
    employee_attr: str = "sAMAccountName"
    name_attr: str = "displayName"
    ldap_bind_factory: Callable[[str, str, "LdapSsoAdapter"], dict[str, Any]] | None = None

    def authenticate(self, employee_id: str, password: str | None = None) -> AuthenticatedIdentity:
        self._require_provider_url()
        if not password:
            raise HTTPException(status_code=401, detail="Password is required for LDAP SSO")

        attributes = (
            self.ldap_bind_factory(employee_id, password, self)
            if self.ldap_bind_factory
            else self._authenticate_with_ldap3(employee_id, password)
        )
        resolved_employee_id = _first_value(attributes.get("employee_id"))
        resolved_employee_id = resolved_employee_id or _first_value(attributes.get(self.employee_attr))
        return AuthenticatedIdentity(
            employee_id=str(resolved_employee_id or employee_id),
            provider=self.provider,
            attributes=attributes,
        )

    def _require_provider_url(self) -> None:
        if not self.provider_url:
            raise HTTPException(
                status_code=500,
                detail="SSO_PROVIDER_URL is required for LDAP/SAML SSO",
            )

    def _authenticate_with_ldap3(self, employee_id: str, password: str) -> dict[str, Any]:
        try:
            from ldap3 import ALL, Connection, Server
            from ldap3.core.exceptions import LDAPBindError, LDAPException
        except ImportError:
            raise HTTPException(
                status_code=500,
                detail="ldap3 package is required for LDAP SSO",
            ) from None

        bind_dn = self.bind_dn_template.format(employee_id=employee_id)
        try:
            server = Server(self.provider_url, get_info=ALL)
            connection = Connection(server, user=bind_dn, password=password, auto_bind=True)
            try:
                attributes = self._search_directory(connection, employee_id)
            finally:
                connection.unbind()
        except LDAPBindError:
            raise HTTPException(status_code=401, detail="Invalid LDAP credentials") from None
        except LDAPException as exc:
            raise HTTPException(status_code=500, detail=f"LDAP SSO failed: {exc}") from exc

        return {**attributes, "employee_id": employee_id}

    def _search_directory(self, connection: Any, employee_id: str) -> dict[str, Any]:
        if not self.search_base:
            return {}

        try:
            from ldap3.utils.conv import escape_filter_chars
        except ImportError:
            escape_filter_chars = str
        query = self.search_filter.format(employee_id=escape_filter_chars(employee_id))
        requested_attributes = list(
            {
                self.employee_attr,
                self.name_attr,
                "mail",
                "email",
                "cn",
                "displayName",
            }
        )
        if not connection.search(self.search_base, query, attributes=requested_attributes):
            return {}
        if not connection.entries:
            return {}
        raw_attributes = connection.entries[0].entry_attributes_as_dict
        return {name: _first_value(value) for name, value in raw_attributes.items()}


@dataclass(frozen=True)
class SamlSsoAdapter:
    provider_url: str
    provider: str = "saml"
    sp_entity_id: str = ""
    acs_url: str = ""
    idp_entity_id: str = ""
    idp_sso_url: str = ""
    idp_x509_cert: str = ""
    employee_attr: str = "employee_id"
    saml_response_validator: Callable[[str, "SamlSsoAdapter"], dict[str, Any]] | None = None

    def authenticate(self, employee_id: str, password: str | None = None) -> AuthenticatedIdentity:
        raise HTTPException(status_code=400, detail="Use SAML ACS endpoint for SAML SSO")

    def authenticate_response(self, saml_response: str) -> AuthenticatedIdentity:
        self._require_provider_url()
        attributes = (
            self.saml_response_validator(saml_response, self)
            if self.saml_response_validator
            else self._authenticate_with_python3_saml(saml_response)
        )
        employee_id = _first_value(attributes.get("employee_id"))
        employee_id = employee_id or _first_value(attributes.get(self.employee_attr))
        employee_id = employee_id or _first_value(attributes.get("NameID"))
        if not employee_id:
            raise HTTPException(status_code=401, detail="SAML assertion does not include employee id")
        return AuthenticatedIdentity(
            employee_id=str(employee_id),
            provider=self.provider,
            attributes=attributes,
        )

    def _require_provider_url(self) -> None:
        if not self.provider_url:
            raise HTTPException(
                status_code=500,
                detail="SSO_PROVIDER_URL is required for LDAP/SAML SSO",
            )

    def _authenticate_with_python3_saml(self, saml_response: str) -> dict[str, Any]:
        try:
            from onelogin.saml2.auth import OneLogin_Saml2_Auth
        except ImportError:
            raise HTTPException(
                status_code=500,
                detail="python3-saml package is required for SAML SSO",
            ) from None

        for name, value in [
            ("SSO_SAML_SP_ENTITY_ID", self.sp_entity_id),
            ("SSO_SAML_ACS_URL", self.acs_url),
            ("SSO_SAML_IDP_ENTITY_ID", self.idp_entity_id),
            ("SSO_SAML_SSO_URL", self.idp_sso_url),
            ("SSO_SAML_X509_CERT", self.idp_x509_cert),
        ]:
            if not value:
                raise HTTPException(status_code=500, detail=f"{name} is required for SAML SSO")

        auth = OneLogin_Saml2_Auth(
            self._request_data(saml_response),
            old_settings=self._settings(),
        )
        auth.process_response()
        if auth.get_errors() or not auth.is_authenticated():
            raise HTTPException(status_code=401, detail="Invalid SAML assertion")

        attributes = {
            name: _first_value(value) for name, value in (auth.get_attributes() or {}).items()
        }
        name_id = auth.get_nameid()
        if name_id:
            attributes["NameID"] = name_id
        return attributes

    def _request_data(self, saml_response: str) -> dict[str, Any]:
        parsed_url = urlparse(self.acs_url)
        return {
            "https": "on" if parsed_url.scheme == "https" else "off",
            "http_host": parsed_url.netloc,
            "server_port": "443" if parsed_url.scheme == "https" else "80",
            "script_name": parsed_url.path,
            "get_data": {},
            "post_data": {"SAMLResponse": saml_response},
        }

    def _settings(self) -> dict[str, Any]:
        return {
            "strict": True,
            "debug": False,
            "sp": {
                "entityId": self.sp_entity_id,
                "assertionConsumerService": {
                    "url": self.acs_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
                },
            },
            "idp": {
                "entityId": self.idp_entity_id,
                "singleSignOnService": {
                    "url": self.idp_sso_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "x509cert": self.idp_x509_cert,
            },
            "security": {
                "wantAssertionsSigned": True,
                "wantMessagesSigned": False,
                "wantNameId": False,
                "requestedAuthnContext": False,
            },
        }


def get_sso_adapter(mode: str | None = None) -> SsoAdapter:
    selected_mode = (mode or settings.sso_mode).lower()
    if selected_mode == "mock":
        return MockSsoAdapter()
    if selected_mode == "broker":
        return BrokerSsoAdapter()
    if selected_mode == "ldap":
        return LdapSsoAdapter(
            provider_url=settings.sso_provider_url,
            bind_dn_template=settings.sso_ldap_bind_dn_template,
            search_base=settings.sso_ldap_search_base,
            search_filter=settings.sso_ldap_search_filter,
            employee_attr=settings.sso_ldap_employee_attr,
            name_attr=settings.sso_ldap_name_attr,
        )
    if selected_mode == "saml":
        return SamlSsoAdapter(
            provider_url=settings.sso_provider_url,
            sp_entity_id=settings.sso_saml_sp_entity_id or settings.sso_client_id,
            acs_url=settings.sso_saml_acs_url,
            idp_entity_id=settings.sso_saml_idp_entity_id,
            idp_sso_url=settings.sso_saml_sso_url,
            idp_x509_cert=settings.sso_saml_x509_cert,
            employee_attr=settings.sso_saml_employee_attr,
        )
    raise HTTPException(status_code=500, detail=f"Unsupported SSO_MODE: {selected_mode}")


def authenticate_employee(employee_id: str, password: str | None = None) -> AuthenticatedIdentity:
    return get_sso_adapter().authenticate(employee_id, password=password)
