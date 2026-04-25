from fastapi.testclient import TestClient

from backend.main import app
from backend.routers import approval as approval_router


class FailingEmailService:
    def send(self, message):
        raise RuntimeError("mail gateway down")


def _unlock_collection(client: TestClient) -> None:
    client.put(
        "/api/admin/collection/status",
        json={"collection_locked": False, "lock_reason": ""},
        headers={"X-Employee-Id": "admin001"},
    )


def test_admin_can_lock_collection_and_block_task_writes():
    client = TestClient(app)
    _unlock_collection(client)

    try:
        lock_response = client.put(
            "/api/admin/collection/status",
            json={"collection_locked": True, "lock_reason": "최종 취합 종료"},
            headers={"X-Employee-Id": "admin001"},
        )

        assert lock_response.status_code == 200
        assert lock_response.json()["collection_locked"] is True
        assert lock_response.json()["lock_reason"] == "최종 취합 종료"

        create_response = client.post(
            "/api/tasks",
            json={
                "organization_id": 1,
                "major_task": "잠금 후 대업무",
                "detail_task": "잠금 후 세부업무",
            },
            headers={"X-Employee-Id": "part001"},
        )
        submit_response = client.post(
            "/api/approvals/submit?org_id=1",
            headers={"X-Employee-Id": "part001"},
        )

        assert create_response.status_code == 423
        assert submit_response.status_code == 423
        assert "취합이 종료" in create_response.json()["detail"]
    finally:
        _unlock_collection(client)


def test_login_task_save_delete_and_export_are_audited():
    client = TestClient(app)
    _unlock_collection(client)

    login_response = client.post("/api/auth/login", json={"employee_id": "part001"})
    assert login_response.status_code == 200

    create_response = client.post(
        "/api/tasks",
        json={
            "organization_id": 1,
            "major_task": "감사 로그 대업무",
            "detail_task": "감사 로그 세부업무",
            "confidential_answers": [["해당 없음"]],
            "national_tech_answers": [["해당 없음"]],
        },
        headers={"X-Employee-Id": "part001"},
    )
    assert create_response.status_code == 201
    task_id = create_response.json()["id"]

    delete_response = client.delete(
        f"/api/tasks/{task_id}",
        headers={"X-Employee-Id": "part001"},
    )
    assert delete_response.status_code == 204

    export_response = client.get(
        "/api/export/excel",
        headers={"X-Employee-Id": "admin001"},
    )
    assert export_response.status_code == 200
    assert "confidential-classification-final-" in export_response.headers["content-disposition"]

    logs = client.get(
        "/api/admin/audit-logs",
        headers={"X-Employee-Id": "admin001"},
    ).json()["items"]
    actions = [log["action"] for log in logs]

    assert "LOGIN" in actions
    assert "TASK_CREATE" in actions
    assert "TASK_DELETE" in actions
    assert "EXPORT_FINAL" in actions

    status = client.get(
        "/api/admin/collection/status",
        headers={"X-Employee-Id": "admin001"},
    ).json()
    assert status["last_export"]["filename"].startswith("confidential-classification-final-")
    assert status["last_export"]["employee_id"] == "admin001"


def test_email_failure_is_visible_to_admin(monkeypatch):
    monkeypatch.setattr(approval_router, "email_service", FailingEmailService())
    client = TestClient(app)
    _unlock_collection(client)
    org = client.post(
        "/api/admin/organizations",
        json={
            "division_name": "메일실패실",
            "division_head_name": "김실장",
            "division_head_id": "div001",
            "part_name": "메일실패파트",
            "part_head_name": "메일실패파트장",
            "part_head_id": "mailfail001",
            "org_type": "DIV_DIRECT",
        },
        headers={"X-Employee-Id": "admin001"},
    ).json()
    task = client.post(
        "/api/tasks",
        json={
            "organization_id": org["id"],
            "major_task": "메일 실패 대업무",
            "detail_task": "메일 실패 세부업무",
            "confidential_answers": [["해당 없음"]],
            "national_tech_answers": [["해당 없음"]],
        },
        headers={"X-Employee-Id": "admin001"},
    ).json()

    try:
        submit_response = client.post(
            f"/api/approvals/submit?org_id={org['id']}",
            headers={"X-Employee-Id": "admin001"},
        )
        assert submit_response.status_code == 201

        failures = client.get(
            "/api/admin/audit-logs?action=EMAIL_SEND&status=FAILED",
            headers={"X-Employee-Id": "admin001"},
        ).json()["items"]

        assert failures
        assert failures[0]["status"] == "FAILED"
        assert "mail gateway down" in failures[0]["message"]
    finally:
        client.delete(f"/api/tasks/{task['id']}", headers={"X-Employee-Id": "admin001"})
        client.delete(f"/api/admin/organizations/{org['id']}", headers={"X-Employee-Id": "admin001"})
