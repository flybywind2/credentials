from fastapi.testclient import TestClient

from backend.main import app


def test_dashboard_summary_uses_database_counts():
    client = TestClient(app)

    orgs = client.get("/api/organizations").json()
    summary = client.get(
        "/api/dashboard/summary",
        headers={"X-Employee-Id": "admin001"},
    ).json()

    assert summary["total_parts"] == len(orgs)
    assert "pending_approvals" in summary
    assert "confidential_task_ratio" in summary


def test_dashboard_detail_endpoints_return_database_series():
    client = TestClient(app)
    headers = {"X-Employee-Id": "admin001"}

    completion = client.get("/api/dashboard/completion-rate", headers=headers)
    approval = client.get("/api/dashboard/approval-status", headers=headers)
    classification = client.get("/api/dashboard/classification-ratio", headers=headers)

    assert completion.status_code == 200
    assert approval.status_code == 200
    assert classification.status_code == 200
    assert "items" in completion.json()
    assert "PENDING" in approval.json()
    assert "confidential" in classification.json()
