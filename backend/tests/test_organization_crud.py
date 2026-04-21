from fastapi.testclient import TestClient

from backend.main import app


def _payload(part_name: str) -> dict:
    return {
        "division_name": "테스트실",
        "division_head_name": "테스트실장",
        "division_head_id": "td1",
        "team_name": "테스트팀",
        "team_head_name": "테스트팀장",
        "team_head_id": "tt1",
        "group_name": "테스트그룹",
        "group_head_name": "테스트그룹장",
        "group_head_id": "tg1",
        "part_name": part_name,
        "part_head_name": "테스트파트장",
        "part_head_id": "tp1",
        "org_type": "NORMAL",
    }


def test_admin_can_create_update_and_delete_organization():
    client = TestClient(app)

    create_response = client.post(
        "/api/admin/organizations",
        json=_payload("테스트파트-CRUD"),
        headers={"X-Employee-Id": "admin001"},
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["email_preview"]["part_head_email"] == "tp1@samsung.com"

    update_response = client.put(
        f"/api/admin/organizations/{created['id']}",
        json={"part_name": "테스트파트-수정"},
        headers={"X-Employee-Id": "admin001"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["part_name"] == "테스트파트-수정"

    list_response = client.get("/api/organizations?part=테스트파트-수정")
    assert list_response.status_code == 200
    assert any(item["id"] == created["id"] for item in list_response.json())

    delete_response = client.delete(
        f"/api/admin/organizations/{created['id']}",
        headers={"X-Employee-Id": "admin001"},
    )
    assert delete_response.status_code == 204


def test_inputter_cannot_create_organization():
    client = TestClient(app)

    response = client.post(
        "/api/admin/organizations",
        json=_payload("권한없는파트"),
        headers={"X-Employee-Id": "part001"},
    )

    assert response.status_code == 403
