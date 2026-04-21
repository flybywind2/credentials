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


def test_non_admin_cannot_read_dashboard_summary():
    client = TestClient(app)

    response = client.get("/api/dashboard/summary", headers={"X-Employee-Id": "part001"})

    assert response.status_code == 403


def test_admin_can_read_dashboard_summary():
    client = TestClient(app)

    response = client.get("/api/dashboard/summary", headers={"X-Employee-Id": "admin001"})

    assert response.status_code == 200
    assert response.json()["total_parts"] >= 1
