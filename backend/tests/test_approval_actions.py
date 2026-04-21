from fastapi.testclient import TestClient

from backend.main import app


def _create_div_direct_submission(client: TestClient, part_name: str) -> dict:
    org = client.post(
        "/api/admin/organizations",
        json={
            "division_name": "처리실",
            "division_head_name": "김실장",
            "division_head_id": "div001",
            "part_name": part_name,
            "part_head_name": "처리파트장",
            "part_head_id": f"{part_name}id",
            "org_type": "DIV_DIRECT",
        },
        headers={"X-Employee-Id": "admin001"},
    ).json()
    task = client.post(
        "/api/tasks",
        json={
            "organization_id": org["id"],
            "major_task": "처리 대업무",
            "detail_task": "처리 세부업무",
            "confidential_answers": [["해당 없음"]],
            "national_tech_answers": [["해당 없음"]],
        },
        headers={"X-Employee-Id": "admin001"},
    ).json()
    approval = client.post(
        f"/api/approvals/submit?org_id={org['id']}",
        headers={"X-Employee-Id": "admin001"},
    ).json()
    return {"org": org, "task": task, "approval": approval}


def test_current_approver_can_approve_final_step():
    client = TestClient(app)
    data = _create_div_direct_submission(client, "승인처리파트")

    response = client.post(
        f"/api/approvals/{data['approval']['id']}/approve",
        headers={"X-Employee-Id": "div001"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "APPROVED"
    assert body["steps"][0]["status"] == "APPROVED"


def test_current_approver_can_reject_with_reason():
    client = TestClient(app)
    data = _create_div_direct_submission(client, "반려처리파트")

    response = client.post(
        f"/api/approvals/{data['approval']['id']}/reject",
        json={"reject_reason": "분류 근거 보완 필요"},
        headers={"X-Employee-Id": "div001"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "REJECTED"
    assert body["reject_reason"] == "분류 근거 보완 필요"


def test_reject_requires_reason():
    client = TestClient(app)
    data = _create_div_direct_submission(client, "반려사유필수파트")

    response = client.post(
        f"/api/approvals/{data['approval']['id']}/reject",
        json={"reject_reason": ""},
        headers={"X-Employee-Id": "div001"},
    )

    assert response.status_code == 422
