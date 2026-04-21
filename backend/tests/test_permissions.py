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


def test_non_admin_cannot_read_dashboard_summary():
    client = TestClient(app)

    response = client.get("/api/dashboard/summary", headers={"X-Employee-Id": "part001"})

    assert response.status_code == 403


def test_admin_can_read_dashboard_summary():
    client = TestClient(app)

    response = client.get("/api/dashboard/summary", headers={"X-Employee-Id": "admin001"})

    assert response.status_code == 200
    assert response.json()["total_parts"] >= 1
