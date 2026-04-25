from fastapi.testclient import TestClient

from backend.main import app


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
    assert response.json()[0]["part_name"] == "AI전략실행파트"


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

    try:
        response = client.get("/api/organizations", headers={"X-Employee-Id": "group001"})

        assert response.status_code == 200
        organization_ids = {item["id"] for item in response.json()}
        assert 1 in organization_ids
        assert other_org_id not in organization_ids
        assert all(
            item["group_head_id"] == "group001" or item["part_head_id"] == "group001"
            for item in response.json()
        )
    finally:
        client.delete(
            f"/api/admin/organizations/{other_org_id}",
            headers=admin_headers,
        )


def test_managed_approver_org_assignment_overrides_org_head_auto_scope():
    client = TestClient(app)
    admin_headers = {"X-Employee-Id": "admin001"}
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
    create_user_response = client.post(
        "/api/admin/users",
        headers=admin_headers,
        json={
            "employee_id": "group001",
            "name": "관리변경그룹장",
            "role": "APPROVER",
            "organization_id": target_org_id,
        },
    )
    assert create_user_response.status_code == 201

    try:
        me_response = client.get("/api/auth/me", headers={"X-Employee-Id": "group001"})
        orgs_response = client.get("/api/organizations", headers={"X-Employee-Id": "group001"})
        group_tasks_response = client.get("/api/tasks/group", headers={"X-Employee-Id": "group001"})

        assert me_response.status_code == 200
        assert me_response.json()["organization_id"] == target_org_id
        assert orgs_response.status_code == 200
        organization_ids = {item["id"] for item in orgs_response.json()}
        assert target_org_id in organization_ids
        assert peer_org_id in organization_ids
        assert 1 not in organization_ids
        assert group_tasks_response.status_code == 200
        task_org_ids = {item["organization_id"] for item in group_tasks_response.json()}
        assert peer_org_id in task_org_ids
        assert 1 not in task_org_ids
    finally:
        client.delete("/api/admin/users/group001", headers=admin_headers)
        client.delete(f"/api/tasks/{create_task_response.json()['id']}", headers=admin_headers)
        client.delete(f"/api/admin/organizations/{peer_org_id}", headers=admin_headers)
        client.delete(f"/api/admin/organizations/{target_org_id}", headers=admin_headers)


def test_managed_approver_anchor_part_does_not_grant_part_writer_permissions():
    client = TestClient(app)
    admin_headers = {"X-Employee-Id": "admin001"}
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
            "employee_id": "group001",
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
            headers={"X-Employee-Id": "group001"},
            json={
                "organization_id": org_id,
                "major_task": "상위관리자가 입력한 대업무",
                "detail_task": "상위관리자가 입력한 세부업무",
            },
        )
        update_task_response = client.put(
            f"/api/tasks/{task_id}",
            headers={"X-Employee-Id": "group001"},
            json={"major_task": "상위관리자가 수정한 대업무"},
        )
        submit_response = client.post(
            f"/api/approvals/submit?org_id={org_id}",
            headers={"X-Employee-Id": "group001"},
        )

        assert create_task_response.status_code == 403
        assert update_task_response.status_code == 403
        assert submit_response.status_code == 403
    finally:
        client.delete("/api/admin/users/group001", headers=admin_headers)
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
