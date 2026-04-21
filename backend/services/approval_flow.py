from collections.abc import Mapping
from typing import Any


def build_approval_path(org: Mapping[str, Any]) -> list[str]:
    org_type = org.get("org_type")
    if org_type == "NORMAL":
        keys = ("group_head_id", "team_head_id", "division_head_id")
    elif org_type == "TEAM_DIRECT":
        keys = ("team_head_id", "division_head_id")
    elif org_type == "DIV_DIRECT":
        keys = ("division_head_id",)
    else:
        raise ValueError(f"Unsupported org_type: {org_type}")

    return [str(org[key]) for key in keys if org.get(key)]
