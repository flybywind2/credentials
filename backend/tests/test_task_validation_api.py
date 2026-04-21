from fastapi.testclient import TestClient

from backend.main import app


def test_task_validation_returns_row_and_field_errors():
    client = TestClient(app)

    response = client.post(
        "/api/tasks/validate",
        json={
            "rows": [
                {"organization_id": 1, "detail_task": "세부업무만 있음"},
                {
                    "organization_id": 1,
                    "major_task": "기밀 대업무",
                    "detail_task": "기밀 세부업무",
                    "confidential_answers": [["설계자료"]],
                },
            ]
        },
        headers={"X-Employee-Id": "part001"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["valid_count"] == 0
    assert body["error_count"] == 3
    assert body["errors"][0]["row_index"] == 0
    assert body["errors"][0]["field"] == "major_task"
    assert body["errors"][1]["field"] == "conf_data_type"
    assert body["errors"][2]["field"] == "conf_owner_user"


def test_task_validation_accepts_valid_rows():
    client = TestClient(app)

    response = client.post(
        "/api/tasks/validate",
        json={
            "rows": [
                {
                    "organization_id": 1,
                    "major_task": "정상 대업무",
                    "detail_task": "정상 세부업무",
                    "confidential_answers": [["해당 없음"]],
                    "national_tech_answers": [["해당 없음"]],
                }
            ]
        },
        headers={"X-Employee-Id": "part001"},
    )

    assert response.status_code == 200
    assert response.json()["valid_count"] == 1
    assert response.json()["error_count"] == 0


def test_task_validation_accepts_question_answer_objects():
    client = TestClient(app)

    response = client.post(
        "/api/tasks/validate",
        json={
            "rows": [
                {
                    "organization_id": 1,
                    "major_task": "객체 답변 대업무",
                    "detail_task": "객체 답변 세부업무",
                    "confidential_answers": [
                        {"question_id": 1, "selected_options": ["설계 자료"]}
                    ],
                    "conf_data_type": "설계 문서",
                    "conf_owner_user": "OWNER",
                    "national_tech_answers": [
                        {"question_id": 1, "selected_options": ["해당 없음"]}
                    ],
                }
            ]
        },
        headers={"X-Employee-Id": "part001"},
    )

    assert response.status_code == 200
    assert response.json()["valid_count"] == 1
    assert response.json()["error_count"] == 0
