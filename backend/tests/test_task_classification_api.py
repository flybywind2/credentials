from fastapi.testclient import TestClient

from backend.main import app


def test_create_task_applies_confidential_and_national_tech_classification():
    client = TestClient(app)

    response = client.post(
        "/api/tasks",
        json={
            "organization_id": 1,
            "major_task": "판정 대업무",
            "detail_task": "판정 세부업무",
            "confidential_answers": [["해당 없음"], ["설계자료"]],
            "national_tech_answers": [["해당 없음"]],
        },
        headers={"X-Employee-Id": "part001"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["is_confidential"] is True
    assert body["is_national_tech"] is False

    client.delete(f"/api/tasks/{body['id']}", headers={"X-Employee-Id": "part001"})


def test_update_task_recalculates_national_tech_classification():
    client = TestClient(app)
    created = client.post(
        "/api/tasks",
        json={
            "organization_id": 1,
            "major_task": "수정 판정 대업무",
            "detail_task": "수정 판정 세부업무",
            "national_tech_answers": [["해당 없음"]],
        },
        headers={"X-Employee-Id": "part001"},
    ).json()

    response = client.put(
        f"/api/tasks/{created['id']}",
        json={"national_tech_answers": [["공정기술"]]},
        headers={"X-Employee-Id": "part001"},
    )

    assert response.status_code == 200
    assert response.json()["is_national_tech"] is True

    client.delete(f"/api/tasks/{created['id']}", headers={"X-Employee-Id": "part001"})
