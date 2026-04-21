from fastapi.testclient import TestClient

from backend.main import app


def _create_approved_request(client: TestClient, part_name: str) -> dict:
    org = client.post(
        "/api/admin/organizations",
        json={
            "division_name": "수정요청실",
            "division_head_name": "김실장",
            "division_head_id": "div001",
            "part_name": part_name,
            "part_head_name": "수정파트장",
            "part_head_id": f"{part_name}id",
            "org_type": "DIV_DIRECT",
        },
        headers={"X-Employee-Id": "admin001"},
    ).json()
    client.post(
        "/api/tasks",
        json={
            "organization_id": org["id"],
            "major_task": "승인 완료 대업무",
            "detail_task": "승인 완료 세부업무",
            "confidential_answers": [["해당 없음"]],
            "national_tech_answers": [["해당 없음"]],
        },
        headers={"X-Employee-Id": "admin001"},
    )
    approval = client.post(
        f"/api/approvals/submit?org_id={org['id']}",
        headers={"X-Employee-Id": "admin001"},
    ).json()
    client.post(
        f"/api/approvals/{approval['id']}/approve",
        headers={"X-Employee-Id": "div001"},
    )
    return {"org": org, "approval": approval}


def test_admin_can_request_edit_after_final_approval():
    client = TestClient(app)
    data = _create_approved_request(client, "승인후수정파트")

    response = client.post(
        f"/api/approvals/{data['approval']['id']}/request-edit",
        json={"reason": "승인 후 기준 변경"},
        headers={"X-Employee-Id": "admin001"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "REJECTED"
    assert "승인 후 기준 변경" in body["reject_reason"]

    tasks = client.get(
        f"/api/tasks?org_id={data['org']['id']}",
        headers={"X-Employee-Id": "admin001"},
    ).json()
    assert {task["status"] for task in tasks} == {"REJECTED"}
