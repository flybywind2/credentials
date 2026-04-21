from fastapi.testclient import TestClient

from backend.main import app


def test_admin_can_update_deadline_and_public_reads_d_day():
    client = TestClient(app)

    update_response = client.put(
        "/api/admin/settings/deadline",
        json={"input_deadline": "2026-04-30", "description": "4월 말 기준 입력 마감"},
        headers={"X-Employee-Id": "admin001"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["input_deadline"] == "2026-04-30"
    assert update_response.json()["description"] == "4월 말 기준 입력 마감"

    read_response = client.get("/api/settings/deadline")

    assert read_response.status_code == 200
    body = read_response.json()
    assert body["input_deadline"] == "2026-04-30"
    assert body["description"] == "4월 말 기준 입력 마감"
    assert "d_day" in body
    assert "is_closed" in body


def test_non_admin_cannot_update_deadline():
    client = TestClient(app)

    response = client.put(
        "/api/admin/settings/deadline",
        json={"input_deadline": "2026-05-01"},
        headers={"X-Employee-Id": "part001"},
    )

    assert response.status_code == 403
