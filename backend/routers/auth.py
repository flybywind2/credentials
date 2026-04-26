from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.services.auth_tokens import create_access_token
from backend.services.current_user import AUTH_COOKIE_NAME, resolve_current_user_from_request
from backend.services.sso import get_sso_adapter
from backend.services.audit import log_audit
from backend.services.user_mapping import resolve_app_user

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    employee_id: str
    password: str | None = None


class BrokerSessionRequest(BaseModel):
    loginid: str
    deptname: str | None = None
    username: str | None = None


def _set_auth_cookie(response: Response, access_token: str) -> None:
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=access_token,
        max_age=settings.sso_token_expire_minutes * 60,
        httponly=True,
        samesite="lax",
    )


@router.get("/sso-config")
def read_sso_config():
    return {
        "sso_mode": settings.sso_mode.lower(),
        "broker_url": settings.broker_url,
        "service_url": settings.service_url,
    }


@router.post("/login")
def login(request: LoginRequest, response: Response, db: Annotated[Session, Depends(get_db)]):
    identity = get_sso_adapter().authenticate(request.employee_id, password=request.password)
    user = resolve_app_user(
        identity.employee_id,
        db=db,
        attributes=identity.attributes,
        provider=identity.provider,
    )
    log_audit(db, action="LOGIN", user=user, target_type="User", target_id=user["employee_id"])
    db.commit()
    access_token = create_access_token(user)
    _set_auth_cookie(response, access_token)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
    }


@router.post("/broker/session")
def create_broker_session(
    payload: BrokerSessionRequest,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
):
    if settings.sso_mode.lower() != "broker":
        raise HTTPException(status_code=400, detail="Broker session is only available in broker mode")
    employee_id = payload.loginid.strip()
    if not employee_id:
        raise HTTPException(status_code=400, detail="loginid is required")
    attributes = {
        "deptname": (payload.deptname or "").strip(),
        "displayName": (payload.username or "").strip(),
    }
    user = resolve_app_user(
        employee_id,
        db=db,
        attributes=attributes,
        provider="broker",
    )
    log_audit(db, action="LOGIN", user=user, target_type="User", target_id=user["employee_id"])
    db.commit()
    access_token = create_access_token(
        {
            **user,
            "broker_deptname": attributes["deptname"],
            "broker_username": attributes["displayName"],
        }
    )
    _set_auth_cookie(response, access_token)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
    }


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key=AUTH_COOKIE_NAME, samesite="lax")
    return {"ok": True}


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
