import csv
from io import StringIO
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_user, require_admin
from backend.models import Organization

router = APIRouter(prefix="/organizations", tags=["organizations"])
admin_router = APIRouter(prefix="/admin/organizations", tags=["admin-organizations"])


class OrganizationCreate(BaseModel):
    division_name: str
    division_head_name: str | None = None
    division_head_id: str | None = None
    team_name: str | None = None
    team_head_name: str | None = None
    team_head_id: str | None = None
    group_name: str | None = None
    group_head_name: str | None = None
    group_head_id: str | None = None
    part_name: str
    part_head_name: str
    part_head_id: str
    org_type: str = "NORMAL"


class OrganizationUpdate(BaseModel):
    division_name: str | None = None
    division_head_name: str | None = None
    division_head_id: str | None = None
    team_name: str | None = None
    team_head_name: str | None = None
    team_head_id: str | None = None
    group_name: str | None = None
    group_head_name: str | None = None
    group_head_id: str | None = None
    part_name: str | None = None
    part_head_name: str | None = None
    part_head_id: str | None = None
    org_type: str | None = None


def _email_preview(org: Organization) -> dict[str, str]:
    preview = {
        "part_head_email": f"{org.part_head_id}@samsung.com",
    }
    if org.division_head_id:
        preview["division_head_email"] = f"{org.division_head_id}@samsung.com"
    if org.team_head_id:
        preview["team_head_email"] = f"{org.team_head_id}@samsung.com"
    if org.group_head_id:
        preview["group_head_email"] = f"{org.group_head_id}@samsung.com"
    return preview


def _serialize(org: Organization) -> dict:
    return {
        "id": org.id,
        "division_name": org.division_name,
        "division_head_name": org.division_head_name,
        "division_head_id": org.division_head_id,
        "team_name": org.team_name,
        "team_head_name": org.team_head_name,
        "team_head_id": org.team_head_id,
        "group_name": org.group_name,
        "group_head_name": org.group_head_name,
        "group_head_id": org.group_head_id,
        "part_name": org.part_name,
        "part_head_name": org.part_head_name,
        "part_head_id": org.part_head_id,
        "org_type": org.org_type,
        "email_preview": _email_preview(org),
    }


def _clean_scope_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _scope_condition(id_column, name_column, scope_id: str | None, scope_name: str | None):
    scope_id = _clean_scope_text(scope_id)
    scope_name = _clean_scope_text(scope_name)
    if not scope_id or not scope_name:
        return None
    return (id_column == scope_id) & (name_column == scope_name)


def _own_organization_condition(user: dict):
    return Organization.id == user["organization_id"]


def _non_blank(column):
    return and_(column.is_not(None), func.trim(column) != "")


def _scoped_organization_query(user: dict):
    query = select(Organization)
    if user["role"] == "ADMIN":
        return query
    if user["role"] == "INPUTTER":
        return query.where(Organization.id == user["organization_id"])
    employee_id = user["employee_id"]
    current_org = user.get("organization") or {}
    if current_org.get("group_head_id") == employee_id:
        group_head_id = current_org.get("group_head_id")
        group_name = current_org.get("group_name")
        condition = _scope_condition(
            Organization.group_head_id,
            Organization.group_name,
            group_head_id,
            group_name,
        )
        if condition is not None:
            return query.where(condition)
        return query.where(_own_organization_condition(user))
    if current_org.get("team_head_id") == employee_id:
        team_head_id = current_org.get("team_head_id")
        team_name = current_org.get("team_name")
        condition = _scope_condition(
            Organization.team_head_id,
            Organization.team_name,
            team_head_id,
            team_name,
        )
        if condition is not None:
            return query.where(condition)
        return query.where(_own_organization_condition(user))
    if current_org.get("division_head_id") == employee_id:
        division_head_id = current_org.get("division_head_id")
        division_name = current_org.get("division_name")
        condition = _scope_condition(
            Organization.division_head_id,
            Organization.division_name,
            division_head_id,
            division_name,
        )
        if condition is not None:
            return query.where(condition)
        return query.where(_own_organization_condition(user))
    if current_org.get("part_head_id") == employee_id:
        return query.where(_own_organization_condition(user))
    if user.get("managed"):
        group_head_id = current_org.get("group_head_id")
        group_name = current_org.get("group_name")
        condition = _scope_condition(
            Organization.group_head_id,
            Organization.group_name,
            group_head_id,
            group_name,
        )
        if condition is not None:
            return query.where(condition)
        return query.where(_own_organization_condition(user))
    return query.where(
        or_(
            and_(Organization.group_head_id == employee_id, _non_blank(Organization.group_name)),
            and_(Organization.team_head_id == employee_id, _non_blank(Organization.team_name)),
            and_(Organization.division_head_id == employee_id, _non_blank(Organization.division_name)),
            Organization.part_head_id == employee_id,
        )
    )


CSV_FIELD_MAP = {
    "실명": "division_name",
    "실장명": "division_head_name",
    "실장ID": "division_head_id",
    "팀명": "team_name",
    "팀장명": "team_head_name",
    "팀장ID": "team_head_id",
    "그룹명": "group_name",
    "그룹장명": "group_head_name",
    "그룹장ID": "group_head_id",
    "파트명": "part_name",
    "파트장명": "part_head_name",
    "파트장ID": "part_head_id",
}


def _clean_text(value: str | None) -> str | None:
    return _clean_scope_text(value)


def _org_type_from_data(data: dict) -> str:
    if not data.get("team_name") and not data.get("group_name"):
        return "DIV_DIRECT"
    if not data.get("group_name"):
        return "TEAM_DIRECT"
    return "NORMAL"


def _normalize_organization_data(data: dict, include_missing_division_heads: bool = True) -> dict:
    normalized = {
        key: _clean_text(value) if isinstance(value, str) or value is None else value
        for key, value in data.items()
    }
    for field in ("division_head_name", "division_head_id"):
        if include_missing_division_heads or field in normalized:
            normalized[field] = normalized.get(field) or ""
    return normalized


def _organization_from_csv_row(row: dict[str, str]) -> Organization:
    data = {target: _clean_text(row.get(source)) for source, target in CSV_FIELD_MAP.items()}
    data["org_type"] = _org_type_from_data(data)
    data = _normalize_organization_data(data)
    return Organization(**data)


@router.get("")
def list_organizations(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
    division: str | None = None,
    team: str | None = None,
    group: str | None = None,
    part: str | None = None,
):
    query = _scoped_organization_query(user)
    if division:
        query = query.where(Organization.division_name.contains(division))
    if team:
        query = query.where(Organization.team_name.contains(team))
    if group:
        query = query.where(Organization.group_name.contains(group))
    if part:
        query = query.where(Organization.part_name.contains(part))
    return [_serialize(org) for org in db.scalars(query).all()]


@admin_router.post("", status_code=status.HTTP_201_CREATED)
def create_organization(
    payload: OrganizationCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
):
    require_admin(user)
    org = Organization(**_normalize_organization_data(payload.model_dump()))
    db.add(org)
    db.commit()
    db.refresh(org)
    return _serialize(org)


@admin_router.post("/import", status_code=status.HTTP_201_CREATED)
async def import_organizations(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
    file: UploadFile = File(...),
):
    require_admin(user)
    raw = await file.read()
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(StringIO(text))
    required_headers = set(CSV_FIELD_MAP)
    if not reader.fieldnames or not required_headers.issubset(set(reader.fieldnames)):
        raise HTTPException(status_code=400, detail="Invalid organization CSV headers")

    organizations = []
    for row in reader:
        org = _organization_from_csv_row(row)
        db.add(org)
        organizations.append(org)
    db.commit()
    for org in organizations:
        db.refresh(org)

    return {
        "imported_count": len(organizations),
        "organizations": [_serialize(org) for org in organizations],
    }


@admin_router.put("/{organization_id}")
def update_organization(
    organization_id: int,
    payload: OrganizationUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
):
    require_admin(user)
    org = db.get(Organization, organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    update_data = _normalize_organization_data(
        payload.model_dump(exclude_unset=True),
        include_missing_division_heads=False,
    )
    for key, value in update_data.items():
        setattr(org, key, value)
    db.commit()
    db.refresh(org)
    return _serialize(org)


@admin_router.delete("/{organization_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_organization(
    organization_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
):
    require_admin(user)
    org = db.get(Organization, organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    db.delete(org)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
