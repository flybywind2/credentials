from typing import Annotated

from fastapi import APIRouter, Depends, Form, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.services.auth_tokens import create_access_token, verify_access_token
from backend.services.sso import get_sso_adapter
from backend.services.user_mapping import resolve_app_user

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    employee_id: str
    password: str | None = None


def _user_from_token_payload(payload: dict) -> dict:
    return {key: value for key, value in payload.items() if key not in {"iat", "exp"}}


def _bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token


@router.post("/login")
def login(request: LoginRequest, db: Annotated[Session, Depends(get_db)]):
    identity = get_sso_adapter().authenticate(request.employee_id, password=request.password)
    user = resolve_app_user(
        identity.employee_id,
        db=db,
        attributes=identity.attributes,
        provider=identity.provider,
    )
    return {
        "access_token": create_access_token(user),
        "token_type": "bearer",
        "user": user,
    }


@router.post("/saml/acs")
def saml_acs(
    db: Annotated[Session, Depends(get_db)],
    saml_response: Annotated[str, Form(alias="SAMLResponse")],
):
    identity = get_sso_adapter().authenticate_response(saml_response)
    user = resolve_app_user(
        identity.employee_id,
        db=db,
        attributes=identity.attributes,
        provider=identity.provider,
    )
    return {
        "access_token": create_access_token(user),
        "token_type": "bearer",
        "user": user,
    }


@router.get("/me")
def read_current_user(
    db: Annotated[Session, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
    x_employee_id: Annotated[str | None, Header()] = None,
):
    token = _bearer_token(authorization)
    if token:
        return _user_from_token_payload(verify_access_token(token))
    if settings.sso_mode.lower() == "mock":
        return resolve_app_user(x_employee_id or "admin001", db=db, provider="mock")
    raise HTTPException(status_code=401, detail="Authentication required")
