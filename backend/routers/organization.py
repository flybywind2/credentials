import csv
from io import StringIO
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_user, require_admin
from backend.models import ApprovalRequest, Organization, PartMember, TaskEntry, User
from backend.services.approver_scope import approver_level_for_user, scope_condition_for_user

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
    if user["role"] == "APPROVER":
        level = approver_level_for_user(user)
        condition = scope_condition_for_user(user, Organization, level)
        if condition is not None:
            return query.where(condition)
        if user.get("managed") or level in {"GROUP", "TEAM", "DIVISION", "PART"}:
            return query.where(_own_organization_condition(user))
    employee_id = user["employee_id"]
    if user.get("organization", {}).get("part_head_id") == employee_id:
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
IMPORT_MODES = {"append", "replace"}
ORGANIZATION_KEY_FIELDS = ("division_name", "team_name", "group_name", "part_name")


def _clean_text(value: str | None) -> str | None:
    return _clean_scope_text(value)


def _validate_import_mode(mode: str | None) -> str:
    normalized = (mode or "append").strip().lower()
    if normalized not in IMPORT_MODES:
        raise HTTPException(status_code=400, detail="mode must be append or replace")
    return normalized


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


def _organization_key(data: dict | Organization) -> tuple[str, str, str, str]:
    return tuple(
        (getattr(data, field, None) if isinstance(data, Organization) else data.get(field)) or ""
        for field in ORGANIZATION_KEY_FIELDS
    )


def _organization_data_from_csv_row(row: dict[str, str]) -> dict:
    data = {target: _clean_text(row.get(source)) for source, target in CSV_FIELD_MAP.items()}
    data["org_type"] = _org_type_from_data(data)
    return _normalize_organization_data(data)


def _update_organization(org: Organization, data: dict) -> Organization:
    for key, value in data.items():
        setattr(org, key, value)
    return org


def _referenced_organization_ids(db: Session, organization_ids: list[int]) -> set[int]:
    if not organization_ids:
        return set()
    referenced: set[int] = set()
    for column in (User.organization_id, TaskEntry.organization_id, ApprovalRequest.organization_id):
        referenced.update(
            org_id
            for org_id in db.scalars(select(column).where(column.in_(organization_ids))).all()
            if org_id is not None
        )
    return referenced


def _stale_organizations_blocking_replace(db: Session, stale_organizations: list[Organization]) -> list[Organization]:
    referenced_ids = _referenced_organization_ids(db, [org.id for org in stale_organizations])
    return [org for org in stale_organizations if org.id in referenced_ids]


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
    mode: str | None = None,
):
    require_admin(user)
    import_mode = _validate_import_mode(mode)
    raw = await file.read()
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(StringIO(text))
    required_headers = set(CSV_FIELD_MAP)
    if not reader.fieldnames or not required_headers.issubset(set(reader.fieldnames)):
        raise HTTPException(status_code=400, detail="Invalid organization CSV headers")

    imported_data_by_key = {}
    for row in reader:
        data = _organization_data_from_csv_row(row)
        imported_data_by_key[_organization_key(data)] = data

    existing_organizations = db.scalars(select(Organization).order_by(Organization.id)).all()
    existing_by_key: dict[tuple[str, str, str, str], list[Organization]] = {}
    for org in existing_organizations:
        existing_by_key.setdefault(_organization_key(org), []).append(org)

    organizations = []
    matched_existing_ids = set()
    for key, data in imported_data_by_key.items():
        existing = existing_by_key.get(key, [])
        if existing:
            org = _update_organization(existing[0], data)
            matched_existing_ids.add(org.id)
        else:
            org = Organization(**data)
            db.add(org)
        organizations.append(org)

    deleted_count = 0
    if import_mode == "replace":
        stale_organizations = [
            org
            for org in existing_organizations
            if org.id not in matched_existing_ids
        ]
        blocking_organizations = _stale_organizations_blocking_replace(db, stale_organizations)
        if blocking_organizations:
            part_names = ", ".join(org.part_name for org in blocking_organizations[:10])
            raise HTTPException(
                status_code=409,
                detail=f"업무/사용자/승인 이력이 있는 조직은 전체 덮어쓰기에서 삭제할 수 없습니다: {part_names}",
            )
        stale_ids = [org.id for org in stale_organizations]
        if stale_ids:
            db.execute(delete(PartMember).where(PartMember.organization_id.in_(stale_ids)))
            for org in stale_organizations:
                db.delete(org)
            deleted_count = len(stale_ids)
    db.commit()
    for org in organizations:
        db.refresh(org)

    return {
        "mode": import_mode,
        "imported_count": len(organizations),
        "deleted_count": deleted_count,
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
