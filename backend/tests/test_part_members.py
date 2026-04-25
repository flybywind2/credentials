from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import get_db
from backend.main import app
from backend.scripts.init_db import initialize_database


CSV_TEXT = """파트명,이름,knox_id
AI전략실행파트,홍길동,hong.gildong
다른파트,김다른,other.member
"""


def _client(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'part-members.db'}"
    initialize_database(database_url=database_url, reset=True)
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_admin_imports_part_members_from_csv_with_knox_id(tmp_path):
    client = _client(tmp_path)

    try:
        response = client.post(
            "/api/part-members/import",
            files={"file": ("members.csv", CSV_TEXT.encode("utf-8"), "text/csv")},
            headers={"X-Employee-Id": "admin001"},
        )

        assert response.status_code == 201
        body = response.json()
        assert body["imported_count"] == 2
        assert body["members"][0]["part_name"] == "AI전략실행파트"
        assert body["members"][0]["name"] == "홍길동"
        assert body["members"][0]["knox_id"] == "hong.gildong"

        listed = client.get("/api/part-members", headers={"X-Employee-Id": "part001"}).json()
        assert any(member["knox_id"] == "hong.gildong" for member in listed)
    finally:
        app.dependency_overrides.clear()


def test_part_member_import_rejects_missing_required_headers(tmp_path):
    client = _client(tmp_path)

    try:
        response = client.post(
            "/api/part-members/import",
            files={"file": ("members.csv", "파트명,이름\nAI전략실행파트,홍길동\n".encode("utf-8"), "text/csv")},
            headers={"X-Employee-Id": "admin001"},
        )

        assert response.status_code == 400
        assert "knox_id" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_inputter_cannot_import_part_members_csv(tmp_path):
    client = _client(tmp_path)

    try:
        response = client.post(
            "/api/part-members/import",
            files={"file": ("members.csv", CSV_TEXT.encode("utf-8"), "text/csv")},
            headers={"X-Employee-Id": "part001"},
        )

        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_inputter_cannot_read_other_part_members(tmp_path):
    client = _client(tmp_path)

    try:
        response = client.get(
            "/api/part-members?org_id=2",
            headers={"X-Employee-Id": "part001"},
        )

        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_task_can_be_assigned_to_imported_part_members_by_knox_id(tmp_path):
    client = _client(tmp_path)

    try:
        client.post(
            "/api/part-members/import",
            files={"file": ("members.csv", CSV_TEXT.encode("utf-8"), "text/csv")},
            headers={"X-Employee-Id": "admin001"},
        )

        create_response = client.post(
            "/api/tasks",
            json={
                "organization_id": 1,
                "sub_part": "배정",
                "major_task": "인력 배정 대업무",
                "detail_task": "인력 배정 세부업무",
                "assignee_knox_ids": ["hong.gildong"],
                "confidential_answers": [["해당 없음"]],
                "national_tech_answers": [["해당 없음"]],
            },
            headers={"X-Employee-Id": "part001"},
        )

        assert create_response.status_code == 201
        created = create_response.json()
        task_id = created["id"]
        assert created["assignees"] == [
            {
                "name": "홍길동",
                "knox_id": "hong.gildong",
                "part_name": "AI전략실행파트",
            }
        ]

        update_response = client.put(
            f"/api/tasks/{task_id}",
            json={"assignee_knox_ids": []},
            headers={"X-Employee-Id": "part001"},
        )

        assert update_response.status_code == 200
        assert update_response.json()["assignees"] == []
    finally:
        app.dependency_overrides.clear()


def test_task_assignment_rejects_unknown_knox_id(tmp_path):
    client = _client(tmp_path)

    try:
        client.post(
            "/api/part-members/import",
            files={"file": ("members.csv", CSV_TEXT.encode("utf-8"), "text/csv")},
            headers={"X-Employee-Id": "admin001"},
        )

        response = client.post(
            "/api/tasks",
            json={
                "organization_id": 1,
                "sub_part": "배정오류",
                "major_task": "인력 배정 오류 대업무",
                "detail_task": "인력 배정 오류 세부업무",
                "assignee_knox_ids": ["missing.member"],
                "confidential_answers": [["해당 없음"]],
                "national_tech_answers": [["해당 없음"]],
            },
            headers={"X-Employee-Id": "part001"},
        )

        assert response.status_code == 400
        assert "파트 인력현황에 없는 담당자" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()
