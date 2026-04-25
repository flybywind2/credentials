from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.dependencies import get_current_user, require_admin
from backend.models import Organization, User
from backend.schemas.common import Role

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


class UserCreate(BaseModel):
    employee_id: str
    name: str
    role: Role
    organization_id: int | None = None


class UserUpdate(BaseModel):
    name: str | None = None
    role: Role | None = None
    organization_id: int | None = None


def _admin_ids() -> set[str]:
    return {
        value.strip()
        for value in settings.sso_admin_employee_ids.split(",")
        if value.strip()
    }


def _organization_path(org: Organization | None) -> str:
    if org is None:
        return ""
    return " / ".join(
        value
        for value in [
            org.division_name,
            org.team_name,
            org.group_name,
            org.part_name,
        ]
        if value
    )


def _serialize_org(org: Organization | None) -> dict | None:
    if org is None:
        return None
    return {
        "id": org.id,
        "division_name": org.division_name,
        "team_name": org.team_name,
        "group_name": org.group_name,
        "part_name": org.part_name,
    }


def _serialize_user(
    *,
    employee_id: str,
    name: str,
    role: str,
    organization: Organization | None,
    managed: bool,
    source: str,
    user_id: int | None = None,
    created_at: datetime | None = None,
) -> dict:
    return {
        "id": user_id,
        "employee_id": employee_id,
        "name": name,
        "role": role,
        "organization_id": organization.id if organization else None,
        "organization": _serialize_org(organization),
        "organization_path": _organization_path(organization),
        "managed": managed,
        "source": source,
        "created_at": created_at.isoformat() if created_at else None,
    }


def _validate_organization(db: Session, organization_id: int | None) -> Organization | None:
    if organization_id is None:
        return None
    organization = db.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return organization


def _require_organization_for_role(role: str, organization_id: int | None) -> None:
    if role != Role.admin and organization_id is None:
        raise HTTPException(
            status_code=400,
            detail="organization_id is required for INPUTTER and APPROVER",
        )


def _ensure_self_admin_not_removed(current_user: dict, employee_id: str, next_role: str) -> None:
    if current_user["employee_id"] == employee_id and current_user["role"] == "ADMIN" and next_role != "ADMIN":
        raise HTTPException(status_code=400, detail="Cannot remove your own admin role")


def _ensure_not_last_admin(db: Session, employee_id: str, next_role: str) -> None:
    if next_role == "ADMIN":
        return
    admin_count = db.scalar(select(func.count(User.id)).where(User.role == "ADMIN")) or 0
    current = db.scalar(select(User).where(User.employee_id == employee_id))
    if current and current.role == "ADMIN" and admin_count <= 1:
        raise HTTPException(status_code=400, detail="At least one managed admin is required")


def _known_users(db: Session) -> list[dict]:
    rows: dict[str, dict] = {}
    organizations_by_id = {org.id: org for org in db.scalars(select(Organization)).all()}
    first_org = next(iter(organizations_by_id.values()), None)

    for user in db.scalars(select(User).order_by(User.employee_id)).all():
        org = organizations_by_id.get(user.organization_id) if user.organization_id else None
        rows[user.employee_id] = _serialize_user(
            employee_id=user.employee_id,
            name=user.name,
            role=user.role,
            organization=org,
            managed=True,
            source="DB",
            user_id=user.id,
            created_at=user.created_at,
        )

    for employee_id in _admin_ids():
        rows.setdefault(
            employee_id,
            _serialize_user(
                employee_id=employee_id,
                name="관리자",
                role="ADMIN",
                organization=first_org,
                managed=False,
                source="설정",
            ),
        )

    for org in organizations_by_id.values():
        candidates = [
            (org.group_head_id, org.group_head_name, "APPROVER"),
            (org.team_head_id, org.team_head_name, "APPROVER"),
            (org.division_head_id, org.division_head_name, "APPROVER"),
            (org.part_head_id, org.part_head_name, "INPUTTER"),
        ]
        for employee_id, name, role in candidates:
            if not employee_id:
                continue
            rows.setdefault(
                employee_id,
                _serialize_user(
                    employee_id=employee_id,
                    name=name or employee_id,
                    role=role,
                    organization=org,
                    managed=False,
                    source="조직장",
                ),
            )

    return sorted(rows.values(), key=lambda item: (item["role"], item["employee_id"]))


@router.get("")
def list_users(
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    require_admin(user)
    return _known_users(db)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    require_admin(user)
    employee_id = payload.employee_id.strip()
    name = payload.name.strip()
    role = str(payload.role)
    if not employee_id or not name:
        raise HTTPException(status_code=400, detail="employee_id and name are required")
    if db.scalar(select(User).where(User.employee_id == employee_id)):
        raise HTTPException(status_code=409, detail="User already exists")
    _require_organization_for_role(role, payload.organization_id)
    organization = _validate_organization(db, payload.organization_id)
    db_user = User(
        employee_id=employee_id,
        name=name,
        role=role,
        organization_id=organization.id if organization else None,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return _serialize_user(
        employee_id=db_user.employee_id,
        name=db_user.name,
        role=db_user.role,
        organization=organization,
        managed=True,
        source="DB",
        user_id=db_user.id,
        created_at=db_user.created_at,
    )


@router.put("/{employee_id}")
def update_user(
    employee_id: str,
    payload: UserUpdate,
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    require_admin(user)
    db_user = db.scalar(select(User).where(User.employee_id == employee_id))
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    next_role = str(payload.role or db_user.role)
    next_organization_id = (
        payload.organization_id
        if "organization_id" in payload.model_fields_set
        else db_user.organization_id
    )
    _ensure_self_admin_not_removed(user, employee_id, next_role)
    _ensure_not_last_admin(db, employee_id, next_role)
    _require_organization_for_role(next_role, next_organization_id)
    organization = _validate_organization(db, next_organization_id)

    if payload.name is not None:
        db_user.name = payload.name.strip()
    db_user.role = next_role
    db_user.organization_id = organization.id if organization else None
    db.commit()
    db.refresh(db_user)
    return _serialize_user(
        employee_id=db_user.employee_id,
        name=db_user.name,
        role=db_user.role,
        organization=organization,
        managed=True,
        source="DB",
        user_id=db_user.id,
        created_at=db_user.created_at,
    )


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    employee_id: str,
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    require_admin(user)
    if user["employee_id"] == employee_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own user")
    _ensure_not_last_admin(db, employee_id, "INPUTTER")
    db_user = db.scalar(select(User).where(User.employee_id == employee_id))
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        db.delete(db_user)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="User is referenced by existing data") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
