from fastapi.testclient import TestClient

from backend.main import app


def test_admin_can_update_and_list_column_tooltips():
    client = TestClient(app)

    update_response = client.put(
        "/api/admin/tooltips/major_task",
        json={"example_text": "대업무 예시"},
        headers={"X-Employee-Id": "admin001"},
    )

    assert update_response.status_code == 200
    assert update_response.json()["column_key"] == "major_task"
    assert update_response.json()["example_text"] == "대업무 예시"

    list_response = client.get(
        "/api/admin/tooltips",
        headers={"X-Employee-Id": "admin001"},
    )

    assert list_response.status_code == 200
    assert any(item["column_key"] == "major_task" for item in list_response.json())


def test_inputter_can_read_public_tooltips_but_cannot_update():
    client = TestClient(app)

    read_response = client.get("/api/tooltips", headers={"X-Employee-Id": "part001"})
    update_response = client.put(
        "/api/admin/tooltips/detail_task",
        json={"example_text": "권한 없는 수정"},
        headers={"X-Employee-Id": "part001"},
    )

    assert read_response.status_code == 200
    assert update_response.status_code == 403
