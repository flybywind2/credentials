from fastapi.testclient import TestClient

from backend.main import app
from backend.routers import approval as approval_router


class FakeEmailService:
    def __init__(self) -> None:
        self.messages = []

    def send(self, message):
        self.messages.append(message)
        return {"status": "sent", "recipients": message.recipients}


def test_submit_and_reject_send_email_notifications(monkeypatch):
    fake = FakeEmailService()
    monkeypatch.setattr(approval_router, "email_service", fake)
    client = TestClient(app)
    org = client.post(
        "/api/admin/organizations",
        json={
            "division_name": "알림실",
            "division_head_name": "김실장",
            "division_head_id": "div001",
            "part_name": "알림파트",
            "part_head_name": "알림파트장",
            "part_head_id": "notify001",
            "org_type": "DIV_DIRECT",
        },
        headers={"X-Employee-Id": "admin001"},
    ).json()
    client.post(
        "/api/tasks",
        json={
            "organization_id": org["id"],
            "major_task": "알림 대업무",
            "detail_task": "알림 세부업무",
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
        f"/api/approvals/{approval['id']}/reject",
        json={"reject_reason": "알림 반려"},
        headers={"X-Employee-Id": "div001"},
    )

    assert fake.messages[0].subject == "승인 요청 제출"
    assert "div001@samsung.com" in fake.messages[0].recipients
    assert f"/approver/approvals/{approval['id']}" in fake.messages[0].body
    assert f"/approver/approvals/{approval['id']}" in fake.messages[0].html_body
    assert "승인 검토 바로가기" in fake.messages[0].html_body
    assert fake.messages[-1].subject == "승인 반려"
    assert "알림 반려" in fake.messages[-1].body
