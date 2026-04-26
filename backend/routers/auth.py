from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, Response
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


def _set_auth_cookie(response: Response, access_token: str) -> None:
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=access_token,
        max_age=settings.sso_token_expire_minutes * 60,
        httponly=True,
        samesite="lax",
    )


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
