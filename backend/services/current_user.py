from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from backend.config import settings
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


def _configured_header(request: Request, header_name: str) -> str:
    if not header_name:
        return ""
    return (request.headers.get(header_name) or "").strip()


def _broker_attributes(request: Request) -> dict[str, str]:
    attributes = {}
    name = _configured_header(request, settings.sso_broker_name_header)
    email = _configured_header(request, settings.sso_broker_email_header)
    deptname = _configured_header(request, settings.sso_broker_dept_header)
    if name:
        attributes["displayName"] = name
    if email:
        attributes["email"] = email
    if deptname:
        attributes["deptname"] = deptname
    return attributes


def resolve_current_user_from_request(
    *,
    db: Session,
    request: Request,
    authorization: str | None,
    x_employee_id: str | None,
) -> dict:
    mode = settings.sso_mode.lower()
    token = _bearer_token(authorization)

    if mode == "mock":
        if x_employee_id:
            return resolve_app_user(x_employee_id.strip(), db=db, provider="mock")
        if token:
            return _strip_token_claims(verify_access_token(token))
        return resolve_app_user("admin001", db=db, provider="mock")

    if mode == "broker":
        employee_id = _configured_header(request, settings.sso_broker_employee_header)
        if not employee_id:
            raise HTTPException(status_code=401, detail="Broker employee header is required")
        return resolve_app_user(
            employee_id,
            db=db,
            attributes=_broker_attributes(request),
            provider="broker",
        )

    if token:
        return _strip_token_claims(verify_access_token(token))
    raise HTTPException(status_code=401, detail="Authentication required")
