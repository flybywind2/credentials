from fastapi.testclient import TestClient

from backend.main import app


def test_pending_approvals_are_filtered_by_current_approver():
    client = TestClient(app)

    response = client.get("/api/approvals/pending", headers={"X-Employee-Id": "group001"})

    assert response.status_code == 200
    body = response.json()
    assert body
    assert {item["current_approver_employee_id"] for item in body} == {"group001"}
    assert "requested_at" in body[0]
    assert body[0]["part_name"] == "AI전략기획파트"


def test_admin_can_see_pending_approvals_from_database():
    client = TestClient(app)

    response = client.get("/api/approvals/pending", headers={"X-Employee-Id": "admin001"})

    assert response.status_code == 200
    assert any(item["status"] == "PENDING" for item in response.json())
