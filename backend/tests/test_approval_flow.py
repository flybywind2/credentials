import pytest

from backend.services.approval_flow import build_approval_path


def test_normal_path_has_group_team_division_heads():
    org = {
        "org_type": "NORMAL",
        "group_head_id": "g1",
        "team_head_id": "t1",
        "division_head_id": "d1",
    }
    assert build_approval_path(org) == ["g1", "t1", "d1"]


def test_team_direct_path_has_team_and_division_heads():
    org = {
        "org_type": "TEAM_DIRECT",
        "team_head_id": "t1",
        "division_head_id": "d1",
    }
    assert build_approval_path(org) == ["t1", "d1"]


def test_div_direct_path_has_division_head_only():
    org = {"org_type": "DIV_DIRECT", "division_head_id": "d1"}
    assert build_approval_path(org) == ["d1"]


def test_unknown_org_type_raises_value_error():
    with pytest.raises(ValueError, match="Unsupported org_type"):
        build_approval_path({"org_type": "UNKNOWN"})
