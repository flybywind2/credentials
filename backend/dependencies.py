from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.services.auth_tokens import verify_access_token
from backend.services.user_mapping import resolve_app_user


def _bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token


def _strip_token_claims(payload: dict) -> dict:
    return {key: value for key, value in payload.items() if key not in {"iat", "exp"}}


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
    x_employee_id: Annotated[str | None, Header()] = None,
) -> dict:
    token = _bearer_token(authorization)
    if token:
        return _strip_token_claims(verify_access_token(token))
    if settings.sso_mode.lower() == "mock":
        return resolve_app_user(x_employee_id or "admin001", db=db, provider="mock")
    raise HTTPException(status_code=401, detail="Authentication required")


def require_admin(user: dict) -> None:
    if user["role"] != "ADMIN":
        raise HTTPException(status_code=403, detail="Insufficient permissions")


def require_approver_or_admin(user: dict) -> None:
    if user["role"] not in {"APPROVER", "ADMIN"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions")


def ensure_can_read_org(user: dict, org_id: int | None) -> None:
    if org_id is None or user["role"] == "ADMIN":
        return
    if user["organization_id"] == org_id:
        return
    if user["role"] == "APPROVER":
        return
    raise HTTPException(status_code=403, detail="Insufficient permissions")


def ensure_can_write_org(user: dict, org_id: int) -> None:
    if user["role"] == "ADMIN":
        return
    if user["role"] == "INPUTTER" and user["organization_id"] == org_id:
        return
    raise HTTPException(status_code=403, detail="Insufficient permissions")
