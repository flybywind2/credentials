from fastapi.testclient import TestClient

from backend.main import app


def test_approval_history_returns_request_and_steps():
    client = TestClient(app)
    org = client.post(
        "/api/admin/organizations",
        json={
            "division_name": "이력실",
            "division_head_name": "김실장",
            "division_head_id": "div001",
            "part_name": "이력파트",
            "part_head_name": "이력파트장",
            "part_head_id": "hist1",
            "org_type": "DIV_DIRECT",
        },
        headers={"X-Employee-Id": "admin001"},
    ).json()
    client.post(
        "/api/tasks",
        json={
            "organization_id": org["id"],
            "major_task": "이력 대업무",
            "detail_task": "이력 세부업무",
        },
        headers={"X-Employee-Id": "admin001"},
    )
    approval = client.post(
        f"/api/approvals/submit?org_id={org['id']}",
        headers={"X-Employee-Id": "admin001"},
    ).json()

    response = client.get(
        f"/api/approvals/{approval['id']}/history",
        headers={"X-Employee-Id": "div001"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == approval["id"]
    assert body["part_name"] == "이력파트"
    assert body["steps"][0]["approver_employee_id"] == "div001"
