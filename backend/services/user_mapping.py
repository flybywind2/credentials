from typing import Any

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models import Organization, User
from backend.seed import ORGANIZATIONS
from backend.services.auth_service import get_mock_user


ORG_FIELDS = (
    "id",
    "division_name",
    "division_head_name",
    "division_head_id",
    "team_name",
    "team_head_name",
    "team_head_id",
    "group_name",
    "group_head_name",
    "group_head_id",
    "part_name",
    "part_head_name",
    "part_head_id",
    "org_type",
)


def _first_value(value: Any) -> Any:
    if isinstance(value, list | tuple):
        return value[0] if value else None
    return value


def _display_name(attributes: dict[str, Any], fallback: str) -> str:
    for key in ("displayName", "name", "cn", "givenName"):
        value = _first_value(attributes.get(key))
        if value:
            return str(value)
    return fallback


def _email(employee_id: str, attributes: dict[str, Any]) -> str:
    value = _first_value(attributes.get("mail")) or _first_value(attributes.get("email"))
    return str(value) if value else f"{employee_id}@samsung.com"


def _org_mapping_required(deptname: str | None) -> HTTPException:
    suffix = f" 현재 SSO 소속: {deptname}" if deptname else ""
    return HTTPException(
        status_code=409,
        detail={
            "code": "ORG_MAPPING_REQUIRED",
            "message": f"소속에 맞는 파트 정보가 없습니다. 담당자에게 정보 등록을 요청해 주세요.{suffix}",
            "deptname": deptname,
        },
    )


def _serialize_org(org: Organization | dict[str, Any] | None) -> dict[str, Any] | None:
    if org is None:
        return None
    if isinstance(org, dict):
        return {field: org.get(field) for field in ORG_FIELDS}
    return {field: getattr(org, field) for field in ORG_FIELDS}


def _first_org(db: Session | None) -> Organization | dict[str, Any] | None:
    if db is None:
        return ORGANIZATIONS[0] if ORGANIZATIONS else None
    return db.scalars(select(Organization).order_by(Organization.id).limit(1)).first()


def _admin_ids() -> set[str]:
    return {
        value.strip()
        for value in settings.sso_admin_employee_ids.split(",")
        if value.strip()
    }


def _user_payload(
    *,
    employee_id: str,
    name: str,
    role: str,
    organization: Organization | dict[str, Any] | None,
    attributes: dict[str, Any],
    provider: str | None,
    managed: bool = False,
) -> dict[str, Any]:
    serialized_org = _serialize_org(organization)
    payload = {
        "employee_id": employee_id,
        "name": name,
        "email": _email(employee_id, attributes),
        "role": role,
        "organization_id": serialized_org["id"] if serialized_org else None,
        "organization": serialized_org,
        "managed": managed,
    }
    if provider:
        payload["sso_provider"] = provider
    return payload


def _resolve_db_user(
    employee_id: str,
    db: Session | None,
    attributes: dict[str, Any],
    provider: str | None,
) -> dict[str, Any] | None:
    if db is None:
        return None

    user = db.scalar(select(User).where(User.employee_id == employee_id))
    if user is None:
        return None
    organization = db.get(Organization, user.organization_id) if user.organization_id else _first_org(db)
    return _user_payload(
        employee_id=employee_id,
        name=_display_name(attributes, user.name),
        role=user.role,
        organization=organization,
        attributes=attributes,
        provider=provider,
        managed=True,
    )


def _resolve_org_head(
    employee_id: str,
    db: Session | None,
    attributes: dict[str, Any],
    provider: str | None,
) -> dict[str, Any] | None:
    if db is None:
        return None

    organizations = db.scalars(
        select(Organization).where(
            or_(
                Organization.part_head_id == employee_id,
                Organization.group_head_id == employee_id,
                Organization.team_head_id == employee_id,
                Organization.division_head_id == employee_id,
            )
        ).order_by(Organization.id)
    ).all()
    if not organizations:
        return None

    def approver_level(org: Organization | None) -> int:
        if org is None:
            return 0
        if org.division_head_id == employee_id:
            return 3
        if org.team_head_id == employee_id:
            return 2
        if org.group_head_id == employee_id:
            return 1
        return 0

    approver_orgs = [org for org in organizations if approver_level(org) > 0]
    approver_org = max(approver_orgs, key=approver_level) if approver_orgs else None
    own_part_org = next((org for org in organizations if org.part_head_id == employee_id), None)
    approver_org_level = approver_level(approver_org)
    use_own_part_anchor = (
        own_part_org is not None
        and approver_org_level > 0
        and approver_level(own_part_org) == approver_org_level
    )
    org = own_part_org if use_own_part_anchor else approver_org or own_part_org or organizations[0]

    if approver_org is not None:
        role = "APPROVER"
        role_org = org if approver_level(org) > 0 else approver_org
        if approver_level(role_org) == 1:
            name = role_org.group_head_name or employee_id
        elif approver_level(role_org) == 2:
            name = role_org.team_head_name or employee_id
        else:
            name = role_org.division_head_name or employee_id
    else:
        role = "INPUTTER"
        name = org.part_head_name

    return _user_payload(
        employee_id=employee_id,
        name=_display_name(attributes, name),
        role=role,
        organization=org,
        attributes=attributes,
        provider=provider,
    )


def _deptname_candidates(deptname: str | None) -> list[str]:
    value = str(deptname or "").strip()
    if not value:
        return []
    without_parentheses = value.split("(", 1)[0].strip()
    candidates = [value]
    if without_parentheses and without_parentheses != value:
        candidates.append(without_parentheses)
    return candidates


def _resolve_broker_dept_user(
    employee_id: str,
    db: Session | None,
    attributes: dict[str, Any],
    provider: str | None,
) -> dict[str, Any] | None:
    if db is None or provider != "broker":
        return None

    candidates = _deptname_candidates(attributes.get("deptname"))
    if not candidates:
        raise _org_mapping_required(None)

    organizations = db.scalars(
        select(Organization)
        .where(
            or_(
                Organization.part_name.in_(candidates),
                Organization.group_name.in_(candidates),
                Organization.team_name.in_(candidates),
                Organization.division_name.in_(candidates),
            )
        )
        .order_by(Organization.id)
    ).all()
    if len(organizations) != 1:
        raise _org_mapping_required(str(attributes.get("deptname") or ""))

    return _user_payload(
        employee_id=employee_id,
        name=_display_name(attributes, employee_id),
        role="INPUTTER",
        organization=organizations[0],
        attributes=attributes,
        provider=provider,
    )


def resolve_app_user(
    employee_id: str,
    db: Session | None = None,
    attributes: dict[str, Any] | None = None,
    provider: str | None = None,
) -> dict[str, Any]:
    directory_attributes = attributes or {}

    db_user = _resolve_db_user(employee_id, db, directory_attributes, provider)
    if db_user:
        return db_user

    org_head_user = _resolve_org_head(employee_id, db, directory_attributes, provider)
    if org_head_user:
        return org_head_user

    if employee_id in _admin_ids():
        return _user_payload(
            employee_id=employee_id,
            name=_display_name(directory_attributes, "관리자"),
            role="ADMIN",
            organization=_first_org(db),
            attributes=directory_attributes,
            provider=provider,
        )

    broker_dept_user = _resolve_broker_dept_user(employee_id, db, directory_attributes, provider)
    if broker_dept_user:
        return broker_dept_user

    mock_user = get_mock_user(employee_id)
    if mock_user:
        return {
            **mock_user,
            "name": _display_name(directory_attributes, mock_user["name"]),
            "email": _email(employee_id, directory_attributes),
            **({"sso_provider": provider} if provider else {}),
        }

    raise HTTPException(status_code=404, detail="Unknown employee_id")
