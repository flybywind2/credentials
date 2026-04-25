from typing import Annotated

from fastapi import APIRouter, Depends, Form, Header, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.auth_tokens import create_access_token
from backend.services.current_user import resolve_current_user_from_request
from backend.services.sso import get_sso_adapter
from backend.services.audit import log_audit
from backend.services.user_mapping import resolve_app_user

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    employee_id: str
    password: str | None = None


@router.post("/login")
def login(request: LoginRequest, db: Annotated[Session, Depends(get_db)]):
    identity = get_sso_adapter().authenticate(request.employee_id, password=request.password)
    user = resolve_app_user(
        identity.employee_id,
        db=db,
        attributes=identity.attributes,
        provider=identity.provider,
    )
    log_audit(db, action="LOGIN", user=user, target_type="User", target_id=user["employee_id"])
    db.commit()
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
    log_audit(db, action="LOGIN", user=user, target_type="User", target_id=user["employee_id"])
    db.commit()
    return {
        "access_token": create_access_token(user),
        "token_type": "bearer",
        "user": user,
    }


@router.get("/me")
def read_current_user(
    db: Annotated[Session, Depends(get_db)],
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    x_employee_id: Annotated[str | None, Header()] = None,
):
    return resolve_current_user_from_request(
        db=db,
        request=request,
        authorization=authorization,
        x_employee_id=x_employee_id,
    )
