import csv
from io import StringIO
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_user, require_admin
from backend.models import Organization, PartMember

router = APIRouter(prefix="/part-members", tags=["part-members"])

CSV_HEADERS = {"파트명", "이름", "knox_id"}


def _serialize(member: PartMember) -> dict:
    return {
        "id": member.id,
        "organization_id": member.organization_id,
        "part_name": member.part_name,
        "name": member.name,
        "knox_id": member.knox_id,
    }


def _target_org_id(user: dict, org_id: int | None) -> int:
    return org_id or user["organization_id"]


def _same_scope(user_org: dict, org: Organization, id_field: str, name_field: str) -> bool:
    scope_id = user_org.get(id_field)
    scope_name = user_org.get(name_field)
    org_id = getattr(org, id_field)
    org_name = getattr(org, name_field)
    if scope_id and scope_name:
        return org_id == scope_id and org_name == scope_name
    if scope_id:
        return org_id == scope_id
    return bool(scope_name and org_name == scope_name)


def _is_actual_approver_scope(user: dict, org: Organization) -> bool:
    employee_id = user["employee_id"]
    current_org = user.get("organization") or {}
    if current_org.get("group_head_id") == employee_id:
        return _same_scope(current_org, org, "group_head_id", "group_name")
    if current_org.get("team_head_id") == employee_id:
        return _same_scope(current_org, org, "team_head_id", "team_name")
    if current_org.get("division_head_id") == employee_id:
        return _same_scope(current_org, org, "division_head_id", "division_name")
    return False


def _ensure_can_read_org(user: dict, db: Session, org_id: int) -> None:
    if user["role"] == "ADMIN":
        return
    if user["role"] == "INPUTTER" and user["organization_id"] == org_id:
        return
    org = db.get(Organization, org_id)
    if user["role"] == "APPROVER" and org is not None and _is_actual_approver_scope(user, org):
        return
    raise HTTPException(status_code=403, detail="Insufficient permissions")


def _required_value(row: dict[str, str], header: str, row_number: int) -> str:
    value = (row.get(header) or "").strip()
    if not value:
        raise HTTPException(
            status_code=400,
            detail=f"{row_number}행의 {header} 값은 필수입니다.",
        )
    return value


def _csv_rows(raw: bytes) -> list[tuple[int, str, str, str]]:
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames or not CSV_HEADERS.issubset(set(reader.fieldnames)):
        raise HTTPException(status_code=400, detail="CSV 헤더는 파트명, 이름, knox_id가 필요합니다.")

    rows = []
    for index, row in enumerate(reader, start=2):
        if not any((value or "").strip() for value in row.values()):
            continue
        part_name = _required_value(row, "파트명", index)
        name = _required_value(row, "이름", index)
        knox_id = _required_value(row, "knox_id", index)
        rows.append((index, part_name, name, knox_id))
    return rows


def _members_from_csv(raw: bytes, organization_id: int) -> list[PartMember]:
    members_by_key: dict[tuple[str, str], PartMember] = {}
    for _, part_name, name, knox_id in _csv_rows(raw):
        members_by_key[(part_name, knox_id)] = PartMember(
            organization_id=organization_id,
            part_name=part_name,
            name=name,
            knox_id=knox_id,
        )
    return list(members_by_key.values())


def _members_from_csv_for_all(db: Session, raw: bytes) -> list[PartMember]:
    organizations_by_part_name: dict[str, list[Organization]] = {}
    for org in db.scalars(select(Organization)).all():
        organizations_by_part_name.setdefault(org.part_name, []).append(org)

    members_by_key: dict[tuple[int, str, str], PartMember] = {}
    for row_number, part_name, name, knox_id in _csv_rows(raw):
        organizations = organizations_by_part_name.get(part_name, [])
        if not organizations:
            raise HTTPException(
                status_code=400,
                detail=f"{row_number}행의 파트명은 조직 정보에 없는 파트명입니다: {part_name}",
            )
        if len(organizations) > 1:
            raise HTTPException(
                status_code=400,
                detail=f"{row_number}행의 파트명이 중복되어 조직을 확정할 수 없습니다: {part_name}",
            )
        organization = organizations[0]
        members_by_key[(organization.id, part_name, knox_id)] = PartMember(
            organization_id=organization.id,
            part_name=part_name,
            name=name,
            knox_id=knox_id,
        )
    return list(members_by_key.values())


@router.get("")
def list_part_members(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
    org_id: int | None = None,
    scope: str | None = None,
):
    if scope == "all":
        require_admin(user)
        members = db.scalars(
            select(PartMember)
            .order_by(PartMember.organization_id, PartMember.part_name, PartMember.name, PartMember.knox_id)
        ).all()
        return [_serialize(member) for member in members]
    target_org_id = _target_org_id(user, org_id)
    _ensure_can_read_org(user, db, target_org_id)
    members = db.scalars(
        select(PartMember)
        .where(PartMember.organization_id == target_org_id)
        .order_by(PartMember.part_name, PartMember.name, PartMember.knox_id)
    ).all()
    return [_serialize(member) for member in members]


@router.post("/import", status_code=status.HTTP_201_CREATED)
async def import_part_members(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
    file: UploadFile = File(...),
    org_id: int | None = None,
    scope: str | None = None,
):
    require_admin(user)
    raw = await file.read()
    if scope == "all":
        members = _members_from_csv_for_all(db, raw)
        db.execute(delete(PartMember))
    else:
        target_org_id = _target_org_id(user, org_id)
        if db.get(Organization, target_org_id) is None:
            raise HTTPException(status_code=404, detail="Organization not found")
        members = _members_from_csv(raw, target_org_id)
        db.execute(delete(PartMember).where(PartMember.organization_id == target_org_id))
    for member in members:
        db.add(member)
    db.commit()
    for member in members:
        db.refresh(member)
    return {
        "imported_count": len(members),
        "members": [_serialize(member) for member in members],
    }
