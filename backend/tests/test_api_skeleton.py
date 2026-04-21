from fastapi.testclient import TestClient

from backend.main import app


def test_auth_me_returns_mock_user():
    client = TestClient(app)
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["employee_id"] == "admin001"


def test_organizations_returns_sample_list():
    client = TestClient(app)
    response = client.get("/api/organizations")
    assert response.status_code == 200
    assert response.json()[0]["part_name"] == "AI전략실행파트"


def test_tasks_returns_sample_entries():
    client = TestClient(app)
    response = client.get("/api/tasks")
    assert response.status_code == 200
    assert response.json()[0]["major_task"] == "기밀 분류 체계 수립"


def test_questions_returns_confidential_and_national_tech_questions():
    client = TestClient(app)
    response = client.get("/api/questions")
    assert response.status_code == 200
    body = response.json()
    assert body["confidential"][0]["options"][0] == "해당 없음"
    assert body["national_tech"][0]["options"][0] == "해당 없음"


def test_pending_approvals_returns_sample_list():
    client = TestClient(app)
    response = client.get("/api/approvals/pending")
    assert response.status_code == 200
    assert response.json()[0]["status"] == "PENDING"


def test_dashboard_summary_returns_counts():
    client = TestClient(app)
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 200
    assert response.json()["total_parts"] >= 1
