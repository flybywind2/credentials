from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Organization
from backend.services.current_user import resolve_current_user_from_request
from backend.services.approver_scope import org_matches_user_scope


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    x_employee_id: Annotated[str | None, Header()] = None,
) -> dict:
    return resolve_current_user_from_request(
        db=db,
        request=request,
        authorization=authorization,
        x_employee_id=x_employee_id,
    )


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


def _is_approver_for_org(user: dict, org: Organization | None) -> bool:
    if org is None:
        return False
    if org.part_head_id == user["employee_id"]:
        return True
    return org_matches_user_scope(user, org, allow_managed_default=False)


def ensure_can_write_org(user: dict, org_id: int, db: Session | None = None) -> None:
    if user["role"] == "ADMIN":
        return
    if user["role"] == "INPUTTER" and user["organization_id"] == org_id:
        return
    organization = user.get("organization") or {}
    if (
        user["role"] == "APPROVER"
        and user["organization_id"] == org_id
        and organization.get("part_head_id") == user["employee_id"]
    ):
        return
    if user["role"] == "APPROVER" and db is not None:
        if _is_approver_for_org(user, db.get(Organization, org_id)):
            return
    raise HTTPException(status_code=403, detail="Insufficient permissions")
