from dataclasses import dataclass, field
from typing import Any, Protocol

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


def get_sso_adapter(mode: str | None = None) -> SsoAdapter:
    selected_mode = (mode or settings.sso_mode).lower()
    if selected_mode == "mock":
        return MockSsoAdapter()
    if selected_mode == "broker":
        return BrokerSsoAdapter()
    raise HTTPException(status_code=500, detail=f"Unsupported SSO_MODE: {selected_mode}")


def authenticate_employee(employee_id: str, password: str | None = None) -> AuthenticatedIdentity:
    return get_sso_adapter().authenticate(employee_id, password=password)
