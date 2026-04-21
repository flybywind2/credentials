from fastapi.testclient import TestClient

from backend.main import app


def test_confidential_questions_are_exposed_separately():
    client = TestClient(app)

    response = client.get("/api/questions/confidential")

    assert response.status_code == 200
    assert response.json()[0]["options"][0] == "해당 없음"


def test_admin_can_create_and_delete_confidential_question_with_none_option():
    client = TestClient(app)

    create_response = client.post(
        "/api/admin/questions/confidential",
        json={"question_text": "신규 기밀 문항", "options": ["설계자료"]},
        headers={"X-Employee-Id": "admin001"},
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["options"] == ["해당 없음", "설계자료"]

    delete_response = client.delete(
        f"/api/admin/questions/confidential/{created['id']}",
        headers={"X-Employee-Id": "admin001"},
    )
    assert delete_response.status_code == 204


def test_admin_can_create_and_delete_national_tech_question_with_none_option():
    client = TestClient(app)

    create_response = client.post(
        "/api/admin/questions/national-tech",
        json={"question_text": "신규 국가핵심기술 문항", "options": ["공정기술"]},
        headers={"X-Employee-Id": "admin001"},
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["options"] == ["해당 없음", "공정기술"]

    delete_response = client.delete(
        f"/api/admin/questions/national-tech/{created['id']}",
        headers={"X-Employee-Id": "admin001"},
    )
    assert delete_response.status_code == 204


def test_inputter_cannot_create_confidential_question():
    client = TestClient(app)

    response = client.post(
        "/api/admin/questions/confidential",
        json={"question_text": "권한 없는 문항", "options": ["설계자료"]},
        headers={"X-Employee-Id": "part001"},
    )

    assert response.status_code == 403


def test_admin_can_reorder_confidential_questions():
    client = TestClient(app)
    first = client.post(
        "/api/admin/questions/confidential",
        json={"question_text": "순서 기밀 문항 A", "options": ["A"], "sort_order": 10},
        headers={"X-Employee-Id": "admin001"},
    ).json()
    second = client.post(
        "/api/admin/questions/confidential",
        json={"question_text": "순서 기밀 문항 B", "options": ["B"], "sort_order": 20},
        headers={"X-Employee-Id": "admin001"},
    ).json()

    response = client.put(
        "/api/admin/questions/confidential/reorder",
        json={"question_ids": [second["id"], first["id"]]},
        headers={"X-Employee-Id": "admin001"},
    )

    assert response.status_code == 200
    questions = client.get("/api/questions/confidential").json()
    ordered_ids = [item["id"] for item in questions if item["id"] in {first["id"], second["id"]}]
    assert ordered_ids == [second["id"], first["id"]]

    client.delete(f"/api/admin/questions/confidential/{first['id']}", headers={"X-Employee-Id": "admin001"})
    client.delete(f"/api/admin/questions/confidential/{second['id']}", headers={"X-Employee-Id": "admin001"})
