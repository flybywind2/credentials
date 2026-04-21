from fastapi.testclient import TestClient

from backend.main import app


def test_admin_can_filter_all_tasks_by_org_and_classification():
    client = TestClient(app)

    response = client.get(
        "/api/admin/tasks?part=AI전략&status=DRAFT&is_confidential=true",
        headers={"X-Employee-Id": "admin001"},
    )

    assert response.status_code == 200
    rows = response.json()["items"]
    assert rows
    assert all(row["part_name"].startswith("AI전략") for row in rows)
    assert all(row["status"] == "DRAFT" for row in rows)
    assert all(row["is_confidential"] is True for row in rows)


def test_inputter_can_read_own_part_status_summary():
    client = TestClient(app)

    response = client.get(
        "/api/tasks/status",
        headers={"X-Employee-Id": "part001"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["organization_id"] == 1
    assert "DRAFT" in body["status_counts"]
