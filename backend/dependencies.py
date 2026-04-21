from typing import Annotated

from fastapi import Header, HTTPException

from backend.services.auth_service import get_mock_user


def get_current_user(x_employee_id: Annotated[str, Header()] = "admin001") -> dict:
    user = get_mock_user(x_employee_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Unknown employee_id")
    return user


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
