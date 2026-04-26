from uuid import uuid4

from fastapi.testclient import TestClient

from backend.database import SessionLocal
from backend.main import app
from backend.routers.organization import _scoped_organization_query


def test_inputter_can_read_own_org_tasks():
    client = TestClient(app)

    response = client.get("/api/tasks?org_id=1", headers={"X-Employee-Id": "part001"})

    assert response.status_code == 200
    rows = response.json()
    assert len(rows) >= 2
    assert {row["organization_id"] for row in rows} == {1}


def test_inputter_cannot_read_other_org_tasks():
    client = TestClient(app)

    response = client.get("/api/tasks?org_id=999", headers={"X-Employee-Id": "part001"})

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"


def test_inputter_cannot_read_pending_approvals():
    client = TestClient(app)

    response = client.get("/api/approvals/pending", headers={"X-Employee-Id": "part001"})

    assert response.status_code == 403


def test_inputter_header_is_not_upgraded_by_stale_admin_bearer_token():
    client = TestClient(app)
    login_response = client.post("/api/auth/login", json={"employee_id": "admin001"})
    token = login_response.json()["access_token"]

    response = client.get(
        "/api/approvals/pending",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Employee-Id": "part001",
        },
    )

    assert response.status_code == 403


def test_approver_can_read_pending_approvals():
    client = TestClient(app)

    response = client.get("/api/approvals/pending", headers={"X-Employee-Id": "group001"})

    assert response.status_code == 200
    assert response.json()[0]["part_name"] == "AI전략기획파트"


def test_approver_cannot_read_non_subordinate_org_tasks():
    client = TestClient(app)
    admin_headers = {"X-Employee-Id": "admin001"}
    org_response = client.post(
        "/api/admin/organizations",
        headers=admin_headers,
        json={
            "division_name": "보안실",
            "division_head_name": "타실장",
            "division_head_id": "other-div",
            "team_name": "보안팀",
            "team_head_name": "타팀장",
            "team_head_id": "other-team",
            "group_name": "보안그룹",
            "group_head_name": "타그룹장",
            "group_head_id": "other-group",
            "part_name": "보안파트",
            "part_head_name": "타파트장",
            "part_head_id": "other-part",
            "org_type": "NORMAL",
        },
    )
    assert org_response.status_code == 201
    org_id = org_response.json()["id"]

    task_response = client.post(
        "/api/tasks",
        headers=admin_headers,
        json={
            "organization_id": org_id,
            "major_task": "타 조직 업무",
            "detail_task": "승인자 산하가 아닌 조직의 업무",
        },
    )
    assert task_response.status_code == 201

    response = client.get(
        f"/api/tasks?org_id={org_id}",
        headers={"X-Employee-Id": "group001"},
    )

    assert response.status_code == 403


def test_approver_organization_list_is_limited_to_subordinate_orgs():
    client = TestClient(app)
    admin_headers = {"X-Employee-Id": "admin001"}
    org_response = client.post(
        "/api/admin/organizations",
        headers=admin_headers,
        json={
            "division_name": "목록보안실",
            "division_head_name": "목록타실장",
            "division_head_id": "list-other-div",
            "team_name": "목록보안팀",
            "team_head_name": "목록타팀장",
            "team_head_id": "list-other-team",
            "group_name": "목록보안그룹",
            "group_head_name": "목록타그룹장",
            "group_head_id": "list-other-group",
            "part_name": "목록보안파트",
            "part_head_name": "목록타파트장",
            "part_head_id": "list-other-part",
            "org_type": "NORMAL",
        },
    )
    assert org_response.status_code == 201
    other_org_id = org_response.json()["id"]
    same_head_other_group_response = client.post(
        "/api/admin/organizations",
        headers=admin_headers,
        json={
            "division_name": "목록타그룹실",
            "division_head_name": "목록타그룹실장",
            "division_head_id": "list-other-group-div",
            "team_name": "목록타그룹팀",
            "team_head_name": "목록타그룹팀장",
            "team_head_id": "list-other-group-team",
            "group_name": "목록타그룹",
            "group_head_name": "박그룹장",
            "group_head_id": "group001",
            "part_name": "목록타그룹파트",
            "part_head_name": "목록타그룹파트장",
            "part_head_id": "list-other-group-part",
            "org_type": "NORMAL",
        },
    )
    assert same_head_other_group_response.status_code == 201
    same_head_other_group_id = same_head_other_group_response.json()["id"]
    try:
        response = client.get("/api/organizations", headers={"X-Employee-Id": "group001"})

        assert response.status_code == 200
        organization_ids = {item["id"] for item in response.json()}
        assert 1 in organization_ids
        assert other_org_id not in organization_ids
        assert same_head_other_group_id not in organization_ids
        assert all(
            item["group_head_id"] == "group001"
            and item["group_name"] == "AI/IT전략그룹"
            for item in response.json()
        )
    finally:
        client.delete(
            f"/api/admin/organizations/{same_head_other_group_id}",
            headers=admin_headers,
        )
        client.delete(
            f"/api/admin/organizations/{other_org_id}",
            headers=admin_headers,
        )


def test_group_approver_scope_ignores_part_head_matches_outside_current_group():
    client = TestClient(app)
    admin_headers = {"X-Employee-Id": "admin001"}
    current_user = client.get("/api/auth/me", headers={"X-Employee-Id": "group001"}).json()
    cross_role_org_response = client.post(
        "/api/admin/organizations",
        headers=admin_headers,
        json={
            "division_name": "범위겸직실",
            "division_head_name": "범위겸직실장",
            "division_head_id": "scope-cross-div",
            "team_name": "범위겸직팀",
            "team_head_name": "범위겸직팀장",
            "team_head_id": "scope-cross-team",
            "group_name": "범위겸직그룹",
            "group_head_name": "범위겸직그룹장",
            "group_head_id": "scope-cross-group",
            "part_name": "범위겸직파트",
            "part_head_name": "박그룹장",
            "part_head_id": "group001",
            "org_type": "NORMAL",
        },
    )
    assert cross_role_org_response.status_code == 201
    cross_role_org_id = cross_role_org_response.json()["id"]

    try:
        with SessionLocal() as db:
            scoped_ids = {
                org.id
                for org in db.scalars(_scoped_organization_query(current_user)).all()
            }

        assert 1 in scoped_ids
        assert cross_role_org_id not in scoped_ids
    finally:
        client.delete(
            f"/api/admin/organizations/{cross_role_org_id}",
            headers=admin_headers,
        )


def test_group_approver_task_reads_are_limited_to_current_group_name():
    client = TestClient(app)
    admin_headers = {"X-Employee-Id": "admin001"}
    org_response = client.post(
        "/api/admin/organizations",
        headers=admin_headers,
        json={
            "division_name": "업무타그룹실",
            "division_head_name": "업무타그룹실장",
            "division_head_id": "task-other-group-div",
            "team_name": "업무타그룹팀",
            "team_head_name": "업무타그룹팀장",
            "team_head_id": "task-other-group-team",
            "group_name": "업무타그룹",
            "group_head_name": "박그룹장",
            "group_head_id": "group001",
            "part_name": "업무타그룹파트",
            "part_head_name": "업무타그룹파트장",
            "part_head_id": "task-other-group-part",
            "org_type": "NORMAL",
        },
    )
    assert org_response.status_code == 201
    org_id = org_response.json()["id"]
    task_response = client.post(
        "/api/tasks",
        headers=admin_headers,
        json={
            "organization_id": org_id,
            "major_task": "업무 타그룹 대업무",
            "detail_task": "같은 그룹장 ID지만 그룹명이 다른 업무",
            "confidential_answers": [["해당 없음"]],
            "national_tech_answers": [["해당 없음"]],
        },
    )
    assert task_response.status_code == 201
    task_id = task_response.json()["id"]

    try:
        direct_response = client.get(
            f"/api/tasks?org_id={org_id}",
            headers={"X-Employee-Id": "group001"},
        )
        status_response = client.get(
            f"/api/tasks/status?org_id={org_id}",
            headers={"X-Employee-Id": "group001"},
        )
        group_response = client.get("/api/tasks/group", headers={"X-Employee-Id": "group001"})

        assert direct_response.status_code == 403
        assert status_response.status_code == 403
        assert task_id not in {row["id"] for row in group_response.json()}
    finally:
        client.delete(f"/api/tasks/{task_id}", headers=admin_headers)
        client.delete(f"/api/admin/organizations/{org_id}", headers=admin_headers)


def test_group_scope_does_not_expand_for_task_or_member_apis_when_group_name_is_missing():
    client = TestClient(app)
    admin_headers = {"X-Employee-Id": "admin001"}
    suffix = uuid4().hex[:8]
    group_head_id = f"blank-scope-group-{suffix}"
    first_org_response = client.post(
        "/api/admin/organizations",
        headers=admin_headers,
        json={
            "division_name": f"공백범위실-{suffix}",
            "division_head_name": "공백범위실장",
            "division_head_id": f"blank-scope-div-{suffix}",
            "team_name": f"공백범위팀-{suffix}",
            "team_head_name": "공백범위팀장",
            "team_head_id": f"blank-scope-team-{suffix}",
            "group_name": None,
            "group_head_name": "공백범위그룹장",
            "group_head_id": group_head_id,
            "part_name": f"공백범위파트A-{suffix}",
            "part_head_name": "공백범위파트장A",
            "part_head_id": f"blank-scope-part-a-{suffix}",
            "org_type": "NORMAL",
        },
    )
    assert first_org_response.status_code == 201
    first_org_id = first_org_response.json()["id"]
    second_org_response = client.post(
        "/api/admin/organizations",
        headers=admin_headers,
        json={
            "division_name": f"공백범위실-{suffix}",
            "division_head_name": "공백범위실장",
            "division_head_id": f"blank-scope-div-{suffix}",
            "team_name": f"공백범위팀-{suffix}",
            "team_head_name": "공백범위팀장",
            "team_head_id": f"blank-scope-team-{suffix}",
            "group_name": None,
            "group_head_name": "공백범위그룹장",
            "group_head_id": group_head_id,
            "part_name": f"공백범위파트B-{suffix}",
            "part_head_name": "공백범위파트장B",
            "part_head_id": f"blank-scope-part-b-{suffix}",
            "org_type": "NORMAL",
        },
    )
    assert second_org_response.status_code == 201
    second_org_id = second_org_response.json()["id"]
    task_response = client.post(
        "/api/tasks",
        headers=admin_headers,
        json={
            "organization_id": second_org_id,
            "major_task": "공백 범위 대업무",
            "detail_task": "그룹명이 없으면 같은 그룹장 ID만으로 확장되면 안 된다.",
            "confidential_answers": [["해당 없음"]],
            "national_tech_answers": [["해당 없음"]],
        },
    )
    assert task_response.status_code == 201
    task_id = task_response.json()["id"]

    try:
        orgs_response = client.get("/api/organizations", headers={"X-Employee-Id": group_head_id})
        direct_tasks_response = client.get(
            f"/api/tasks?org_id={second_org_id}",
            headers={"X-Employee-Id": group_head_id},
        )
        status_response = client.get(
            f"/api/tasks/status?org_id={second_org_id}",
            headers={"X-Employee-Id": group_head_id},
        )
        group_tasks_response = client.get("/api/tasks/group", headers={"X-Employee-Id": group_head_id})
        members_response = client.get(
            f"/api/part-members?org_id={second_org_id}",
            headers={"X-Employee-Id": group_head_id},
        )

        assert orgs_response.status_code == 200
        assert [item["id"] for item in orgs_response.json()] == [first_org_id]
        assert direct_tasks_response.status_code == 403
        assert status_response.status_code == 403
        assert task_id not in {item["id"] for item in group_tasks_response.json()}
        assert members_response.status_code == 403
    finally:
        client.delete(f"/api/tasks/{task_id}", headers=admin_headers)
        client.delete(f"/api/admin/organizations/{second_org_id}", headers=admin_headers)
        client.delete(f"/api/admin/organizations/{first_org_id}", headers=admin_headers)


def test_upper_approver_menus_keep_manager_scope_when_also_part_head_elsewhere():
    client = TestClient(app)
    admin_headers = {"X-Employee-Id": "admin001"}
    created_org_ids: list[int] = []
    created_task_ids: list[int] = []

    def create_org(employee_id: str, level: str, suffix: str, outside: bool = False) -> int:
        label = f"상위메뉴{level}{suffix}"
        payload = {
            "division_name": f"{label}실",
            "division_head_name": f"{label}실장",
            "division_head_id": employee_id if level == "division" and not outside else f"{label}-div",
            "team_name": f"{label}팀",
            "team_head_name": f"{label}팀장",
            "team_head_id": employee_id if level == "team" and not outside else f"{label}-team",
            "group_name": f"{label}그룹",
            "group_head_name": f"{label}그룹장",
            "group_head_id": employee_id if level == "group" and not outside else f"{label}-group",
            "part_name": f"{label}파트",
            "part_head_name": f"{label}파트장",
            "part_head_id": employee_id if outside else f"{label}-part",
            "org_type": "NORMAL",
        }
        if not outside and suffix == "B":
            if level == "group":
                payload["group_name"] = f"상위메뉴{level}A그룹"
            if level == "team":
                payload["team_name"] = f"상위메뉴{level}A팀"
            if level == "division":
                payload["division_name"] = f"상위메뉴{level}A실"
        response = client.post("/api/admin/organizations", headers=admin_headers, json=payload)
        assert response.status_code == 201
        org_id = response.json()["id"]
        created_org_ids.append(org_id)
        return org_id

    try:
        for level in ("group", "team", "division"):
            employee_id = f"upper-menu-{level}-{uuid4().hex[:8]}"
            base_org_id = create_org(employee_id, level, "A")
            peer_org_id = create_org(employee_id, level, "B")
            outside_part_org_id = create_org(employee_id, level, "X", outside=True)
            task_response = client.post(
                "/api/tasks",
                headers=admin_headers,
                json={
                    "organization_id": peer_org_id,
                    "major_task": f"{level} 하위메뉴 대업무",
                    "detail_task": f"{level} 하위메뉴 세부업무",
                    "confidential_answers": [["해당 없음"]],
                    "national_tech_answers": [["해당 없음"]],
                },
            )
            assert task_response.status_code == 201
            task_id = task_response.json()["id"]
            created_task_ids.append(task_id)

            headers = {"X-Employee-Id": employee_id}
            me_response = client.get("/api/auth/me", headers=headers)
            orgs_response = client.get("/api/organizations", headers=headers)
            tasks_response = client.get(f"/api/tasks?org_id={peer_org_id}", headers=headers)
            status_response = client.get(f"/api/tasks/status?org_id={peer_org_id}", headers=headers)
            members_response = client.get(f"/api/part-members?org_id={peer_org_id}", headers=headers)
            group_tasks_response = client.get("/api/tasks/group", headers=headers)
            subordinate_response = client.get("/api/approvals/subordinate-status", headers=headers)

            assert me_response.status_code == 200
            assert me_response.json()["role"] == "APPROVER"
            assert me_response.json()["organization"]["id"] == base_org_id
            assert orgs_response.status_code == 200
            organization_ids = {item["id"] for item in orgs_response.json()}
            assert base_org_id in organization_ids
            assert peer_org_id in organization_ids
            assert outside_part_org_id not in organization_ids
            assert tasks_response.status_code == 200
            assert status_response.status_code == 200
            assert members_response.status_code == 200
            assert group_tasks_response.status_code == 200
            assert task_id in {item["id"] for item in group_tasks_response.json()}
            assert subordinate_response.status_code == 200
            subordinate_org_ids = {
                org_id
                for row in subordinate_response.json()["rows"]
                for org_id in row["organization_ids"]
            }
            assert base_org_id in subordinate_org_ids
            assert peer_org_id in subordinate_org_ids
            assert outside_part_org_id not in subordinate_org_ids
    finally:
        for task_id in reversed(created_task_ids):
            client.delete(f"/api/tasks/{task_id}", headers=admin_headers)
        for org_id in reversed(created_org_ids):
            client.delete(f"/api/admin/organizations/{org_id}", headers=admin_headers)


def test_managed_approver_org_assignment_overrides_org_head_auto_scope():
    client = TestClient(app)
    admin_headers = {"X-Employee-Id": "admin001"}
    managed_employee_id = f"managed{uuid4().hex[:8]}"
    auto_scope_org_response = client.post(
        "/api/admin/organizations",
        headers=admin_headers,
        json={
            "division_name": "자동조직실",
            "division_head_name": "자동조직실장",
            "division_head_id": f"{managed_employee_id}-div",
            "team_name": "자동조직팀",
            "team_head_name": "자동조직팀장",
            "team_head_id": f"{managed_employee_id}-team",
            "group_name": "자동조직그룹",
            "group_head_name": "자동조직그룹장",
            "group_head_id": managed_employee_id,
            "part_name": "자동조직파트",
            "part_head_name": "자동조직파트장",
            "part_head_id": f"{managed_employee_id}-part",
            "org_type": "NORMAL",
        },
    )
    assert auto_scope_org_response.status_code == 201
    auto_scope_org_id = auto_scope_org_response.json()["id"]
    target_org_response = client.post(
        "/api/admin/organizations",
        headers=admin_headers,
        json={
            "division_name": "관리변경실",
            "division_head_name": "관리변경실장",
            "division_head_id": "managed-div",
            "team_name": "관리변경팀",
            "team_head_name": "관리변경팀장",
            "team_head_id": "managed-team",
            "group_name": "관리변경그룹",
            "group_head_name": "관리변경그룹장",
            "group_head_id": "managed-group",
            "part_name": "관리변경파트A",
            "part_head_name": "관리변경파트장A",
            "part_head_id": "managed-part-a",
            "org_type": "NORMAL",
        },
    )
    assert target_org_response.status_code == 201
    target_org_id = target_org_response.json()["id"]
    peer_org_response = client.post(
        "/api/admin/organizations",
        headers=admin_headers,
        json={
            "division_name": "관리변경실",
            "division_head_name": "관리변경실장",
            "division_head_id": "managed-div",
            "team_name": "관리변경팀",
            "team_head_name": "관리변경팀장",
            "team_head_id": "managed-team",
            "group_name": "관리변경그룹",
            "group_head_name": "관리변경그룹장",
            "group_head_id": "managed-group",
            "part_name": "관리변경파트B",
            "part_head_name": "관리변경파트장B",
            "part_head_id": "managed-part-b",
            "org_type": "NORMAL",
        },
    )
    assert peer_org_response.status_code == 201
    peer_org_id = peer_org_response.json()["id"]
    same_head_other_group_response = client.post(
        "/api/admin/organizations",
        headers=admin_headers,
        json={
            "division_name": "관리변경실",
            "division_head_name": "관리변경실장",
            "division_head_id": "managed-div",
            "team_name": "관리변경팀",
            "team_head_name": "관리변경팀장",
            "team_head_id": "managed-team",
            "group_name": "관리변경타그룹",
            "group_head_name": "관리변경그룹장",
            "group_head_id": "managed-group",
            "part_name": "관리변경파트C",
            "part_head_name": "관리변경파트장C",
            "part_head_id": "managed-part-c",
            "org_type": "NORMAL",
        },
    )
    assert same_head_other_group_response.status_code == 201
    same_head_other_group_id = same_head_other_group_response.json()["id"]
    create_task_response = client.post(
        "/api/tasks",
        headers=admin_headers,
        json={
            "organization_id": peer_org_id,
            "major_task": "관리 변경 그룹 대업무",
            "detail_task": "관리 변경 그룹 세부업무",
        },
    )
    assert create_task_response.status_code == 201
    create_off_scope_task_response = client.post(
        "/api/tasks",
        headers=admin_headers,
        json={
            "organization_id": same_head_other_group_id,
            "major_task": "관리 변경 타그룹 대업무",
            "detail_task": "같은 group_head_id지만 다른 group_name 업무",
        },
    )
    assert create_off_scope_task_response.status_code == 201
    create_user_response = client.post(
        "/api/admin/users",
        headers=admin_headers,
        json={
            "employee_id": managed_employee_id,
            "name": "관리변경그룹장",
            "role": "APPROVER",
            "organization_id": target_org_id,
        },
    )
    assert create_user_response.status_code == 201

    try:
        me_response = client.get("/api/auth/me", headers={"X-Employee-Id": managed_employee_id})
        orgs_response = client.get("/api/organizations", headers={"X-Employee-Id": managed_employee_id})
        group_tasks_response = client.get("/api/tasks/group", headers={"X-Employee-Id": managed_employee_id})

        assert me_response.status_code == 200
        assert me_response.json()["organization_id"] == target_org_id
        assert orgs_response.status_code == 200
        organization_ids = {item["id"] for item in orgs_response.json()}
        assert target_org_id in organization_ids
        assert peer_org_id in organization_ids
        assert same_head_other_group_id not in organization_ids
        assert auto_scope_org_id not in organization_ids
        assert group_tasks_response.status_code == 200
        task_org_ids = {item["organization_id"] for item in group_tasks_response.json()}
        assert peer_org_id in task_org_ids
        assert same_head_other_group_id not in task_org_ids
        assert auto_scope_org_id not in task_org_ids
    finally:
        client.delete(f"/api/admin/users/{managed_employee_id}", headers=admin_headers)
        client.delete(f"/api/tasks/{create_off_scope_task_response.json()['id']}", headers=admin_headers)
        client.delete(f"/api/tasks/{create_task_response.json()['id']}", headers=admin_headers)
        client.delete(f"/api/admin/organizations/{same_head_other_group_id}", headers=admin_headers)
        client.delete(f"/api/admin/organizations/{peer_org_id}", headers=admin_headers)
        client.delete(f"/api/admin/organizations/{target_org_id}", headers=admin_headers)
        client.delete(f"/api/admin/organizations/{auto_scope_org_id}", headers=admin_headers)


def test_managed_team_head_can_read_all_groups_in_assigned_team():
    client = TestClient(app)
    admin_headers = {"X-Employee-Id": "admin001"}
    managed_employee_id = f"managed-team-{uuid4().hex[:8]}"
    first_org_response = client.post(
        "/api/admin/organizations",
        headers=admin_headers,
        json={
            "division_name": "관리팀권한실",
            "division_head_name": "관리팀권한실장",
            "division_head_id": "managed-team-scope-div",
            "team_name": "관리팀권한팀",
            "team_head_name": "관리팀권한팀장",
            "team_head_id": managed_employee_id,
            "group_name": "관리팀권한그룹A",
            "group_head_name": "관리팀권한그룹장A",
            "group_head_id": "managed-team-scope-group-a",
            "part_name": "관리팀권한파트A",
            "part_head_name": "관리팀권한파트장A",
            "part_head_id": "managed-team-scope-part-a",
            "org_type": "NORMAL",
        },
    )
    assert first_org_response.status_code == 201
    first_org_id = first_org_response.json()["id"]
    peer_org_response = client.post(
        "/api/admin/organizations",
        headers=admin_headers,
        json={
            "division_name": "관리팀권한실",
            "division_head_name": "관리팀권한실장",
            "division_head_id": "managed-team-scope-div",
            "team_name": "관리팀권한팀",
            "team_head_name": "관리팀권한팀장",
            "team_head_id": managed_employee_id,
            "group_name": "관리팀권한그룹B",
            "group_head_name": "관리팀권한그룹장B",
            "group_head_id": "managed-team-scope-group-b",
            "part_name": "관리팀권한파트B",
            "part_head_name": "관리팀권한파트장B",
            "part_head_id": "managed-team-scope-part-b",
            "org_type": "NORMAL",
        },
    )
    assert peer_org_response.status_code == 201
    peer_org_id = peer_org_response.json()["id"]
    other_team_org_response = client.post(
        "/api/admin/organizations",
        headers=admin_headers,
        json={
            "division_name": "관리팀권한실",
            "division_head_name": "관리팀권한실장",
            "division_head_id": "managed-team-scope-div",
            "team_name": "관리팀권한타팀",
            "team_head_name": "관리팀권한팀장",
            "team_head_id": managed_employee_id,
            "group_name": "관리팀권한타그룹",
            "group_head_name": "관리팀권한타그룹장",
            "group_head_id": "managed-team-scope-other-group",
            "part_name": "관리팀권한타파트",
            "part_head_name": "관리팀권한타파트장",
            "part_head_id": "managed-team-scope-other-part",
            "org_type": "NORMAL",
        },
    )
    assert other_team_org_response.status_code == 201
    other_team_org_id = other_team_org_response.json()["id"]
    peer_task_response = client.post(
        "/api/tasks",
        headers=admin_headers,
        json={
            "organization_id": peer_org_id,
            "major_task": "관리 팀장 범위 대업무",
            "detail_task": "팀장 할당 사용자가 다른 그룹 업무를 조회한다.",
        },
    )
    assert peer_task_response.status_code == 201
    other_task_response = client.post(
        "/api/tasks",
        headers=admin_headers,
        json={
            "organization_id": other_team_org_id,
            "major_task": "관리 팀장 제외 대업무",
            "detail_task": "같은 팀장 ID지만 팀명이 다른 업무는 제외한다.",
        },
    )
    assert other_task_response.status_code == 201
    create_user_response = client.post(
        "/api/admin/users",
        headers=admin_headers,
        json={
            "employee_id": managed_employee_id,
            "name": "관리팀권한팀장",
            "role": "APPROVER",
            "organization_id": first_org_id,
        },
    )
    assert create_user_response.status_code == 201

    try:
        orgs_response = client.get("/api/organizations", headers={"X-Employee-Id": managed_employee_id})
        peer_tasks_response = client.get(
            f"/api/tasks?org_id={peer_org_id}",
            headers={"X-Employee-Id": managed_employee_id},
        )
        other_tasks_response = client.get(
            f"/api/tasks?org_id={other_team_org_id}",
            headers={"X-Employee-Id": managed_employee_id},
        )
        group_tasks_response = client.get("/api/tasks/group", headers={"X-Employee-Id": managed_employee_id})

        assert orgs_response.status_code == 200
        organization_ids = {item["id"] for item in orgs_response.json()}
        assert first_org_id in organization_ids
        assert peer_org_id in organization_ids
        assert other_team_org_id not in organization_ids
        assert peer_tasks_response.status_code == 200
        assert other_tasks_response.status_code == 403
        group_task_org_ids = {item["organization_id"] for item in group_tasks_response.json()}
        assert peer_org_id in group_task_org_ids
        assert other_team_org_id not in group_task_org_ids
    finally:
        client.delete(f"/api/admin/users/{managed_employee_id}", headers=admin_headers)
        client.delete(f"/api/tasks/{other_task_response.json()['id']}", headers=admin_headers)
        client.delete(f"/api/tasks/{peer_task_response.json()['id']}", headers=admin_headers)
        client.delete(f"/api/admin/organizations/{other_team_org_id}", headers=admin_headers)
        client.delete(f"/api/admin/organizations/{peer_org_id}", headers=admin_headers)
        client.delete(f"/api/admin/organizations/{first_org_id}", headers=admin_headers)


def test_group_head_scope_uses_group_name_when_peer_rows_have_different_head_id():
    client = TestClient(app)
    admin_headers = {"X-Employee-Id": "admin001"}
    suffix = uuid4().hex[:8]
    employee_id = f"group-name-scope-{suffix}"
    group_name = f"그룹명범위그룹-{suffix}"
    created_org_ids: list[int] = []
    created_task_ids: list[int] = []

    def create_org(
        *,
        group_head_id: str,
        group: str,
        part: str,
        part_head_id: str,
    ) -> int:
        response = client.post(
            "/api/admin/organizations",
            headers=admin_headers,
            json={
                "division_name": f"그룹명범위실-{suffix}",
                "division_head_name": "그룹명범위실장",
                "division_head_id": f"group-name-div-{suffix}",
                "team_name": f"그룹명범위팀-{suffix}",
                "team_head_name": "그룹명범위팀장",
                "team_head_id": f"group-name-team-{suffix}",
                "group_name": group,
                "group_head_name": f"{group}장",
                "group_head_id": group_head_id,
                "part_name": part,
                "part_head_name": f"{part}장",
                "part_head_id": part_head_id,
                "org_type": "NORMAL",
            },
        )
        assert response.status_code == 201
        org_id = response.json()["id"]
        created_org_ids.append(org_id)
        return org_id

    try:
        anchor_org_id = create_org(
            group_head_id=employee_id,
            group=group_name,
            part=f"그룹명범위파트A-{suffix}",
            part_head_id=f"group-name-part-a-{suffix}",
        )
        peer_org_id = create_org(
            group_head_id=f"csv-other-group-head-{suffix}",
            group=group_name,
            part=f"그룹명범위파트B-{suffix}",
            part_head_id=f"group-name-part-b-{suffix}",
        )
        other_group_org_id = create_org(
            group_head_id=employee_id,
            group=f"다른그룹명범위그룹-{suffix}",
            part=f"다른그룹명범위파트-{suffix}",
            part_head_id=f"group-name-part-c-{suffix}",
        )
        task_response = client.post(
            "/api/tasks",
            headers=admin_headers,
            json={
                "organization_id": peer_org_id,
                "major_task": "그룹명 범위 대업무",
                "detail_task": "같은 그룹명 안의 다른 group_head_id 행도 그룹장 하위로 본다.",
                "confidential_answers": [["해당 없음"]],
                "national_tech_answers": [["해당 없음"]],
            },
        )
        assert task_response.status_code == 201
        task_id = task_response.json()["id"]
        created_task_ids.append(task_id)

        headers = {"X-Employee-Id": employee_id}
        orgs_response = client.get("/api/organizations", headers=headers)
        direct_tasks_response = client.get(f"/api/tasks?org_id={peer_org_id}", headers=headers)
        status_response = client.get(f"/api/tasks/status?org_id={peer_org_id}", headers=headers)
        group_tasks_response = client.get("/api/tasks/group", headers=headers)
        members_response = client.get(f"/api/part-members?org_id={peer_org_id}", headers=headers)
        subordinate_response = client.get("/api/approvals/subordinate-status", headers=headers)

        assert orgs_response.status_code == 200
        organization_ids = {item["id"] for item in orgs_response.json()}
        assert anchor_org_id in organization_ids
        assert peer_org_id in organization_ids
        assert other_group_org_id not in organization_ids
        assert direct_tasks_response.status_code == 200
        assert task_id in {item["id"] for item in direct_tasks_response.json()}
        assert status_response.status_code == 200
        assert group_tasks_response.status_code == 200
        assert task_id in {item["id"] for item in group_tasks_response.json()}
        assert members_response.status_code == 200
        assert subordinate_response.status_code == 200
        subordinate_org_ids = {
            org_id
            for row in subordinate_response.json()["rows"]
            for org_id in row["organization_ids"]
        }
        assert anchor_org_id in subordinate_org_ids
        assert peer_org_id in subordinate_org_ids
        assert other_group_org_id not in subordinate_org_ids
    finally:
        for task_id in reversed(created_task_ids):
            client.delete(f"/api/tasks/{task_id}", headers=admin_headers)
        for org_id in reversed(created_org_ids):
            client.delete(f"/api/admin/organizations/{org_id}", headers=admin_headers)


def test_team_head_scope_uses_team_name_when_peer_rows_have_different_head_id():
    client = TestClient(app)
    admin_headers = {"X-Employee-Id": "admin001"}
    suffix = uuid4().hex[:8]
    employee_id = f"team-name-scope-{suffix}"
    team_name = f"팀명범위팀-{suffix}"
    created_org_ids: list[int] = []
    created_task_ids: list[int] = []

    def create_org(
        *,
        team_head_id: str,
        team: str,
        group: str,
        part: str,
        part_head_id: str,
    ) -> int:
        response = client.post(
            "/api/admin/organizations",
            headers=admin_headers,
            json={
                "division_name": f"팀명범위실-{suffix}",
                "division_head_name": "팀명범위실장",
                "division_head_id": f"team-name-div-{suffix}",
                "team_name": team,
                "team_head_name": f"{team}장",
                "team_head_id": team_head_id,
                "group_name": group,
                "group_head_name": f"{group}장",
                "group_head_id": f"{group}-head",
                "part_name": part,
                "part_head_name": f"{part}장",
                "part_head_id": part_head_id,
                "org_type": "NORMAL",
            },
        )
        assert response.status_code == 201
        org_id = response.json()["id"]
        created_org_ids.append(org_id)
        return org_id

    try:
        anchor_org_id = create_org(
            team_head_id=employee_id,
            team=team_name,
            group=f"팀명범위그룹A-{suffix}",
            part=f"팀명범위파트A-{suffix}",
            part_head_id=f"team-name-part-a-{suffix}",
        )
        peer_org_id = create_org(
            team_head_id=f"csv-other-team-head-{suffix}",
            team=team_name,
            group=f"팀명범위그룹B-{suffix}",
            part=f"팀명범위파트B-{suffix}",
            part_head_id=f"team-name-part-b-{suffix}",
        )
        other_team_org_id = create_org(
            team_head_id=employee_id,
            team=f"다른팀명범위팀-{suffix}",
            group=f"다른팀명범위그룹-{suffix}",
            part=f"다른팀명범위파트-{suffix}",
            part_head_id=f"team-name-part-c-{suffix}",
        )
        task_response = client.post(
            "/api/tasks",
            headers=admin_headers,
            json={
                "organization_id": peer_org_id,
                "major_task": "팀명 범위 대업무",
                "detail_task": "같은 팀명 안의 다른 team_head_id 행도 팀장 하위로 본다.",
                "confidential_answers": [["해당 없음"]],
                "national_tech_answers": [["해당 없음"]],
            },
        )
        assert task_response.status_code == 201
        task_id = task_response.json()["id"]
        created_task_ids.append(task_id)

        headers = {"X-Employee-Id": employee_id}
        orgs_response = client.get("/api/organizations", headers=headers)
        direct_tasks_response = client.get(f"/api/tasks?org_id={peer_org_id}", headers=headers)
        status_response = client.get(f"/api/tasks/status?org_id={peer_org_id}", headers=headers)
        group_tasks_response = client.get("/api/tasks/group", headers=headers)
        members_response = client.get(f"/api/part-members?org_id={peer_org_id}", headers=headers)
        subordinate_response = client.get("/api/approvals/subordinate-status", headers=headers)

        assert orgs_response.status_code == 200
        organization_ids = {item["id"] for item in orgs_response.json()}
        assert anchor_org_id in organization_ids
        assert peer_org_id in organization_ids
        assert other_team_org_id not in organization_ids
        assert direct_tasks_response.status_code == 200
        assert task_id in {item["id"] for item in direct_tasks_response.json()}
        assert status_response.status_code == 200
        assert group_tasks_response.status_code == 200
        assert task_id in {item["id"] for item in group_tasks_response.json()}
        assert members_response.status_code == 200
        assert subordinate_response.status_code == 200
        subordinate_org_ids = {
            org_id
            for row in subordinate_response.json()["rows"]
            for org_id in row["organization_ids"]
        }
        assert anchor_org_id in subordinate_org_ids
        assert peer_org_id in subordinate_org_ids
        assert other_team_org_id not in subordinate_org_ids
    finally:
        for task_id in reversed(created_task_ids):
            client.delete(f"/api/tasks/{task_id}", headers=admin_headers)
        for org_id in reversed(created_org_ids):
            client.delete(f"/api/admin/organizations/{org_id}", headers=admin_headers)


def test_division_head_scope_uses_division_name_when_peer_rows_have_different_head_id():
    client = TestClient(app)
    admin_headers = {"X-Employee-Id": "admin001"}
    suffix = uuid4().hex[:8]
    employee_id = f"division-name-scope-{suffix}"
    division_name = f"실명범위실-{suffix}"
    created_org_ids: list[int] = []
    created_task_ids: list[int] = []

    def create_org(
        *,
        division_head_id: str,
        division: str,
        team: str,
        part: str,
        part_head_id: str,
    ) -> int:
        response = client.post(
            "/api/admin/organizations",
            headers=admin_headers,
            json={
                "division_name": division,
                "division_head_name": f"{division}장",
                "division_head_id": division_head_id,
                "team_name": team,
                "team_head_name": f"{team}장",
                "team_head_id": f"{team}-head",
                "group_name": f"{team}그룹",
                "group_head_name": f"{team}그룹장",
                "group_head_id": f"{team}-group",
                "part_name": part,
                "part_head_name": f"{part}장",
                "part_head_id": part_head_id,
                "org_type": "NORMAL",
            },
        )
        assert response.status_code == 201
        org_id = response.json()["id"]
        created_org_ids.append(org_id)
        return org_id

    try:
        anchor_org_id = create_org(
            division_head_id=employee_id,
            division=division_name,
            team=f"실명범위팀A-{suffix}",
            part=f"실명범위파트A-{suffix}",
            part_head_id=f"division-name-part-a-{suffix}",
        )
        peer_org_id = create_org(
            division_head_id=f"csv-other-division-head-{suffix}",
            division=division_name,
            team=f"실명범위팀B-{suffix}",
            part=f"실명범위파트B-{suffix}",
            part_head_id=f"division-name-part-b-{suffix}",
        )
        other_division_org_id = create_org(
            division_head_id=employee_id,
            division=f"다른실명범위실-{suffix}",
            team=f"다른실명범위팀-{suffix}",
            part=f"다른실명범위파트-{suffix}",
            part_head_id=f"division-name-part-c-{suffix}",
        )
        task_response = client.post(
            "/api/tasks",
            headers=admin_headers,
            json={
                "organization_id": peer_org_id,
                "major_task": "실명 범위 대업무",
                "detail_task": "같은 실명 안의 다른 division_head_id 행도 실장 하위로 본다.",
                "confidential_answers": [["해당 없음"]],
                "national_tech_answers": [["해당 없음"]],
            },
        )
        assert task_response.status_code == 201
        task_id = task_response.json()["id"]
        created_task_ids.append(task_id)

        headers = {"X-Employee-Id": employee_id}
        orgs_response = client.get("/api/organizations", headers=headers)
        direct_tasks_response = client.get(f"/api/tasks?org_id={peer_org_id}", headers=headers)
        status_response = client.get(f"/api/tasks/status?org_id={peer_org_id}", headers=headers)
        group_tasks_response = client.get("/api/tasks/group", headers=headers)
        members_response = client.get(f"/api/part-members?org_id={peer_org_id}", headers=headers)
        subordinate_response = client.get("/api/approvals/subordinate-status", headers=headers)

        assert orgs_response.status_code == 200
        organization_ids = {item["id"] for item in orgs_response.json()}
        assert anchor_org_id in organization_ids
        assert peer_org_id in organization_ids
        assert other_division_org_id not in organization_ids
        assert direct_tasks_response.status_code == 200
        assert task_id in {item["id"] for item in direct_tasks_response.json()}
        assert status_response.status_code == 200
        assert group_tasks_response.status_code == 200
        assert task_id in {item["id"] for item in group_tasks_response.json()}
        assert members_response.status_code == 200
        assert subordinate_response.status_code == 200
        subordinate_org_ids = {
            org_id
            for row in subordinate_response.json()["rows"]
            for org_id in row["organization_ids"]
        }
        assert anchor_org_id in subordinate_org_ids
        assert peer_org_id in subordinate_org_ids
        assert other_division_org_id not in subordinate_org_ids
    finally:
        for task_id in reversed(created_task_ids):
            client.delete(f"/api/tasks/{task_id}", headers=admin_headers)
        for org_id in reversed(created_org_ids):
            client.delete(f"/api/admin/organizations/{org_id}", headers=admin_headers)


def test_managed_approver_anchor_part_does_not_grant_part_writer_permissions():
    client = TestClient(app)
    admin_headers = {"X-Employee-Id": "admin001"}
    managed_employee_id = f"upper{uuid4().hex[:8]}"
    org_response = client.post(
        "/api/admin/organizations",
        headers=admin_headers,
        json={
            "division_name": "상위관리실",
            "division_head_name": "상위관리실장",
            "division_head_id": "upper-div",
            "team_name": "상위관리팀",
            "team_head_name": "상위관리팀장",
            "team_head_id": "upper-team",
            "group_name": "상위관리그룹",
            "group_head_name": "상위관리그룹장",
            "group_head_id": "upper-group",
            "part_name": "상위관리기준파트",
            "part_head_name": "실제파트장",
            "part_head_id": "upper-part",
            "org_type": "NORMAL",
        },
    )
    assert org_response.status_code == 201
    org_id = org_response.json()["id"]
    create_user_response = client.post(
        "/api/admin/users",
        headers=admin_headers,
        json={
            "employee_id": managed_employee_id,
            "name": "상위관리자",
            "role": "APPROVER",
            "organization_id": org_id,
        },
    )
    assert create_user_response.status_code == 201
    task_response = client.post(
        "/api/tasks",
        headers=admin_headers,
        json={
            "organization_id": org_id,
            "major_task": "상위관리 기준 대업무",
            "detail_task": "상위관리 기준 세부업무",
            "confidential_answers": [["해당 없음"]],
            "national_tech_answers": [["해당 없음"]],
        },
    )
    assert task_response.status_code == 201
    task_id = task_response.json()["id"]

    try:
        create_task_response = client.post(
            "/api/tasks",
            headers={"X-Employee-Id": managed_employee_id},
            json={
                "organization_id": org_id,
                "major_task": "상위관리자가 입력한 대업무",
                "detail_task": "상위관리자가 입력한 세부업무",
            },
        )
        update_task_response = client.put(
            f"/api/tasks/{task_id}",
            headers={"X-Employee-Id": managed_employee_id},
            json={"major_task": "상위관리자가 수정한 대업무"},
        )
        submit_response = client.post(
            f"/api/approvals/submit?org_id={org_id}",
            headers={"X-Employee-Id": managed_employee_id},
        )

        assert create_task_response.status_code == 403
        assert update_task_response.status_code == 403
        assert submit_response.status_code == 403
    finally:
        client.delete(f"/api/admin/users/{managed_employee_id}", headers=admin_headers)
        client.delete(f"/api/tasks/{task_id}", headers=admin_headers)
        client.delete(f"/api/admin/organizations/{org_id}", headers=admin_headers)


def test_non_admin_cannot_read_dashboard_summary():
    client = TestClient(app)

    response = client.get("/api/dashboard/summary", headers={"X-Employee-Id": "part001"})

    assert response.status_code == 403


def test_admin_can_read_dashboard_summary():
    client = TestClient(app)

    response = client.get("/api/dashboard/summary", headers={"X-Employee-Id": "admin001"})

    assert response.status_code == 200
    assert response.json()["total_parts"] >= 1
