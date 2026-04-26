from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Organization
from backend.services.current_user import resolve_current_user_from_request


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
    employee_id = user["employee_id"]
    current_org = user.get("organization") or {}
    if current_org.get("group_head_id") == employee_id:
        if _same_scope(current_org, org, "group_head_id", "group_name"):
            return True
    elif current_org.get("team_head_id") == employee_id:
        if _same_scope(current_org, org, "team_head_id", "team_name"):
            return True
    elif current_org.get("division_head_id") == employee_id:
        if _same_scope(current_org, org, "division_head_id", "division_name"):
            return True
    return org.part_head_id == employee_id


def _same_scope(user_org: dict, org: Organization, id_field: str, name_field: str) -> bool:
    scope_id = user_org.get(id_field)
    scope_name = user_org.get(name_field)
    org_id = getattr(org, id_field)
    org_name = getattr(org, name_field)
    return bool(scope_id and scope_name and org_id == scope_id and org_name == scope_name)


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
