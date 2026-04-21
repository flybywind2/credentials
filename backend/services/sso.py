from dataclasses import dataclass
from typing import Protocol

from fastapi import HTTPException

from backend.config import settings
from backend.services.auth_service import get_mock_user


class SsoAdapter(Protocol):
    def authenticate(self, employee_id: str) -> dict:
        pass


@dataclass(frozen=True)
class MockSsoAdapter:
    def authenticate(self, employee_id: str) -> dict:
        user = get_mock_user(employee_id)
        if user is None:
            raise HTTPException(status_code=404, detail="Unknown employee_id")
        return user


@dataclass(frozen=True)
class DirectorySsoAdapter:
    provider: str
    provider_url: str = ""

    def authenticate(self, employee_id: str) -> dict:
        if not self.provider_url:
            raise HTTPException(
                status_code=500,
                detail="SSO_PROVIDER_URL is required for LDAP/SAML SSO",
            )
        user = get_mock_user(employee_id)
        if user is None:
            raise HTTPException(status_code=404, detail="Unknown employee_id")
        return {**user, "sso_provider": self.provider}


@dataclass(frozen=True)
class LdapSsoAdapter(DirectorySsoAdapter):
    provider: str = "ldap"


@dataclass(frozen=True)
class SamlSsoAdapter(DirectorySsoAdapter):
    provider: str = "saml"


def get_sso_adapter(mode: str | None = None) -> SsoAdapter:
    selected_mode = (mode or settings.sso_mode).lower()
    if selected_mode == "mock":
        return MockSsoAdapter()
    if selected_mode == "ldap":
        return LdapSsoAdapter(provider_url=settings.sso_provider_url)
    if selected_mode == "saml":
        return SamlSsoAdapter(provider_url=settings.sso_provider_url)
    raise HTTPException(status_code=500, detail=f"Unsupported SSO_MODE: {selected_mode}")


def authenticate_employee(employee_id: str) -> dict:
    return get_sso_adapter().authenticate(employee_id)
