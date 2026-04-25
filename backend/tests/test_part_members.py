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
            "/api/part-members/import?org_id=1",
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


def test_admin_imports_part_members_for_all_parts_from_single_csv(tmp_path):
    client = _client(tmp_path)

    try:
        org_response = client.post(
            "/api/admin/organizations",
            json={
                "division_name": "일괄실",
                "division_head_name": "일괄실장",
                "division_head_id": "bulk-div",
                "team_name": "일괄팀",
                "team_head_name": "일괄팀장",
                "team_head_id": "bulk-team",
                "group_name": "일괄그룹",
                "group_head_name": "일괄그룹장",
                "group_head_id": "bulk-group",
                "part_name": "일괄파트",
                "part_head_name": "일괄파트장",
                "part_head_id": "bulk-part",
                "org_type": "NORMAL",
            },
            headers={"X-Employee-Id": "admin001"},
        )
        assert org_response.status_code == 201
        org_id = org_response.json()["id"]
        csv_text = """파트명,이름,knox_id
AI전략실행파트,홍길동,hong.gildong
일괄파트,김일괄,bulk.member
"""

        response = client.post(
            "/api/part-members/import?scope=all",
            files={"file": ("members.csv", csv_text.encode("utf-8"), "text/csv")},
            headers={"X-Employee-Id": "admin001"},
        )

        assert response.status_code == 201
        body = response.json()
        assert body["imported_count"] == 2
        assert {member["organization_id"] for member in body["members"]} == {1, org_id}
        own_members = client.get("/api/part-members?org_id=1", headers={"X-Employee-Id": "part001"}).json()
        bulk_members = client.get(f"/api/part-members?org_id={org_id}", headers={"X-Employee-Id": "bulk-group"}).json()
        assert [member["knox_id"] for member in own_members] == ["hong.gildong"]
        assert [member["knox_id"] for member in bulk_members] == ["bulk.member"]
    finally:
        app.dependency_overrides.clear()


def test_all_part_member_import_rejects_unknown_or_duplicate_part_name(tmp_path):
    client = _client(tmp_path)

    try:
        duplicate_response = client.post(
            "/api/admin/organizations",
            json={
                "division_name": "중복실",
                "division_head_name": "중복실장",
                "division_head_id": "dup-div",
                "team_name": "중복팀",
                "team_head_name": "중복팀장",
                "team_head_id": "dup-team",
                "group_name": "중복그룹",
                "group_head_name": "중복그룹장",
                "group_head_id": "dup-group",
                "part_name": "AI전략실행파트",
                "part_head_name": "중복파트장",
                "part_head_id": "dup-part",
                "org_type": "NORMAL",
            },
            headers={"X-Employee-Id": "admin001"},
        )
        assert duplicate_response.status_code == 201

        duplicate_import = client.post(
            "/api/part-members/import?scope=all",
            files={"file": ("members.csv", "파트명,이름,knox_id\nAI전략실행파트,홍길동,hong.gildong\n".encode("utf-8"), "text/csv")},
            headers={"X-Employee-Id": "admin001"},
        )
        unknown_import = client.post(
            "/api/part-members/import?scope=all",
            files={"file": ("members.csv", "파트명,이름,knox_id\n없는파트,홍길동,hong.gildong\n".encode("utf-8"), "text/csv")},
            headers={"X-Employee-Id": "admin001"},
        )

        assert duplicate_import.status_code == 400
        assert "파트명이 중복" in duplicate_import.json()["detail"]
        assert unknown_import.status_code == 400
        assert "조직 정보에 없는 파트명" in unknown_import.json()["detail"]
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


def test_managed_approver_anchor_part_does_not_grant_part_member_access(tmp_path):
    client = _client(tmp_path)

    try:
        org_response = client.post(
            "/api/admin/organizations",
            json={
                "division_name": "상위관리실",
                "division_head_name": "상위관리실장",
                "division_head_id": "upper-div",
                "team_name": "상위관리팀",
                "team_head_name": "상위관리팀장",
                "team_head_id": "upper-team",
                "group_name": "상위관리그룹",
                "group_head_name": "상위관리그룹장",
                "group_head_id": "upper-group",
                "part_name": "상위관리기준파트",
                "part_head_name": "실제파트장",
                "part_head_id": "upper-part",
                "org_type": "NORMAL",
            },
            headers={"X-Employee-Id": "admin001"},
        )
        assert org_response.status_code == 201
        org_id = org_response.json()["id"]
        client.post(
            f"/api/part-members/import?org_id={org_id}",
            files={"file": ("members.csv", "파트명,이름,knox_id\n상위관리기준파트,홍길동,hong.gildong\n".encode("utf-8"), "text/csv")},
            headers={"X-Employee-Id": "admin001"},
        )
        create_user_response = client.post(
            "/api/admin/users",
            json={
                "employee_id": "group001",
                "name": "상위관리자",
                "role": "APPROVER",
                "organization_id": org_id,
            },
            headers={"X-Employee-Id": "admin001"},
        )
        assert create_user_response.status_code == 201

        response = client.get(
            f"/api/part-members?org_id={org_id}",
            headers={"X-Employee-Id": "group001"},
        )

        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_actual_group_head_can_read_subordinate_part_members(tmp_path):
    client = _client(tmp_path)

    try:
        client.post(
            "/api/part-members/import",
            files={"file": ("members.csv", CSV_TEXT.encode("utf-8"), "text/csv")},
            headers={"X-Employee-Id": "admin001"},
        )

        response = client.get(
            "/api/part-members?org_id=1",
            headers={"X-Employee-Id": "group001"},
        )

        assert response.status_code == 200
        assert any(member["knox_id"] == "hong.gildong" for member in response.json())
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
