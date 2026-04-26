from typing import Any


ApproverLevel = str


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    stripped = str(value).strip()
    return stripped or None


def _same_text(left: Any, right: Any) -> bool:
    left_text = _clean_text(left)
    right_text = _clean_text(right)
    return bool(left_text and right_text and left_text == right_text)


def _mock_level_from_employee_id(employee_id: str | None) -> ApproverLevel | None:
    value = (employee_id or "").lower()
    if value.startswith("div") and value[3:].isdigit():
        return "DIVISION"
    if value.startswith("team") and value[4:].isdigit():
        return "TEAM"
    return None


def approver_level_for_user(user: dict, allow_managed_default: bool = True) -> ApproverLevel | None:
    current_org = user.get("organization") or {}
    employee_id = _clean_text(user.get("employee_id"))
    name = _clean_text(user.get("name"))
    managed = bool(user.get("managed"))

    if current_org.get("division_head_id") == employee_id:
        return "DIVISION"
    if current_org.get("team_head_id") == employee_id:
        return "TEAM"
    if current_org.get("group_head_id") == employee_id:
        return "GROUP"
    if current_org.get("part_head_id") == employee_id:
        return "PART"

    if managed:
        if _same_text(current_org.get("division_head_name"), name):
            return "DIVISION"
        if _same_text(current_org.get("team_head_name"), name):
            return "TEAM"
        if _same_text(current_org.get("group_head_name"), name):
            return "GROUP"
        mock_level = _mock_level_from_employee_id(employee_id)
        if mock_level:
            return mock_level
        if allow_managed_default:
            return "GROUP"

    return None


def approval_role_for_level(level: ApproverLevel | None) -> str | None:
    return {
        "GROUP": "그룹장",
        "TEAM": "팀장",
        "DIVISION": "실장",
    }.get(level or "")


def status_scope_label_for_user(user: dict) -> str:
    if user["role"] == "ADMIN":
        return "전체현황"
    return {
        "GROUP": "파트현황",
        "TEAM": "그룹현황",
        "DIVISION": "실현황",
    }.get(approver_level_for_user(user) or "", "하위 조직 현황")


def status_unit_for_org(user: dict, org: Any) -> tuple[str, str, str]:
    level = approver_level_for_user(user)
    if user["role"] == "ADMIN" or level == "GROUP":
        return "PART", f"part:{org.id}", org.part_name
    if level == "TEAM":
        if org.group_name:
            return "GROUP", f"group:{org.team_name}:{org.group_name}", org.group_name
        return "PART", f"part:{org.id}", org.part_name
    if level == "DIVISION":
        if org.team_name:
            return "TEAM", f"team:{org.division_name}:{org.team_name}", org.team_name
        return "PART", f"part:{org.id}", org.part_name
    return "PART", f"part:{org.id}", org.part_name


def same_scope_values(
    scope_id: str | None,
    scope_name: str | None,
    org_id: str | None,
    org_name: str | None,
) -> bool:
    return bool(scope_id and scope_name and org_id == scope_id and org_name == scope_name)


def org_matches_user_scope(
    user: dict,
    org: Any | None,
    level: ApproverLevel | None = None,
    allow_managed_default: bool = True,
) -> bool:
    if org is None:
        return False
    current_org = user.get("organization") or {}
    resolved_level = level or approver_level_for_user(
        user,
        allow_managed_default=allow_managed_default,
    )
    if resolved_level == "DIVISION":
        return _same_text(current_org.get("division_name"), org.division_name)
    if resolved_level == "TEAM":
        return _same_text(current_org.get("team_name"), org.team_name)
    if resolved_level == "GROUP":
        return _same_text(current_org.get("group_name"), org.group_name)
    if resolved_level == "PART":
        return org.id == user.get("organization_id")
    return False


def _scope_condition(id_column: Any, name_column: Any, scope_id: str | None, scope_name: str | None):
    scope_id = _clean_text(scope_id)
    scope_name = _clean_text(scope_name)
    if not scope_id or not scope_name:
        return None
    return (id_column == scope_id) & (name_column == scope_name)


def _name_scope_condition(name_column: Any, scope_name: str | None):
    scope_name = _clean_text(scope_name)
    if not scope_name:
        return None
    return name_column == scope_name


def scope_condition_for_user(user: dict, organization_model: Any, level: ApproverLevel | None = None):
    current_org = user.get("organization") or {}
    resolved_level = level or approver_level_for_user(user)
    if resolved_level == "DIVISION":
        return _name_scope_condition(
            organization_model.division_name,
            current_org.get("division_name"),
        )
    if resolved_level == "TEAM":
        return _name_scope_condition(
            organization_model.team_name,
            current_org.get("team_name"),
        )
    if resolved_level == "GROUP":
        return _name_scope_condition(
            organization_model.group_name,
            current_org.get("group_name"),
        )
    if resolved_level == "PART":
        return organization_model.id == user["organization_id"]
    return None
