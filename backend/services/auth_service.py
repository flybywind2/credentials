from backend.seed import ORGANIZATIONS


def _email(employee_id: str) -> str:
    return f"{employee_id}@samsung.com"


def get_mock_user(employee_id: str) -> dict | None:
    organization = ORGANIZATIONS[0]
    users = {
        "admin001": {"name": "관리자", "role": "ADMIN", "organization": organization},
        organization["part_head_id"]: {
            "name": organization["part_head_name"],
            "role": "INPUTTER",
            "organization": organization,
        },
        organization["group_head_id"]: {
            "name": organization["group_head_name"],
            "role": "APPROVER",
            "organization": organization,
        },
        organization["team_head_id"]: {
            "name": organization["team_head_name"],
            "role": "APPROVER",
            "organization": organization,
        },
        organization["division_head_id"]: {
            "name": organization["division_head_name"],
            "role": "APPROVER",
            "organization": organization,
        },
    }

    user = users.get(employee_id)
    if not user:
        return None

    return {
        "employee_id": employee_id,
        "name": user["name"],
        "email": _email(employee_id),
        "role": user["role"],
        "organization_id": user["organization"]["id"],
        "organization": user["organization"],
    }
