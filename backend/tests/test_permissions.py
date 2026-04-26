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
