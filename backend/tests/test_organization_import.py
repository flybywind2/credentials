from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import get_db
from backend.main import app
from backend.models import Organization
from backend.scripts.init_db import initialize_database


CSV_TEXT = """실명,실장명,실장ID,팀명,팀장명,팀장ID,그룹명,그룹장명,그룹장ID,파트명,파트장명,파트장ID
수입실,수입실장,impd1,수입팀,수입팀장,impt1,수입그룹,수입그룹장,impg1,수입파트,수입파트장,impp1
"""


CSV_HEADER = "실명,실장명,실장ID,팀명,팀장명,팀장ID,그룹명,그룹장명,그룹장ID,파트명,파트장명,파트장ID"


def _csv_line(org: dict) -> str:
    return ",".join(
        str(org.get(key) or "")
        for key in [
            "division_name",
            "division_head_name",
            "division_head_id",
            "team_name",
            "team_head_name",
            "team_head_id",
            "group_name",
            "group_head_name",
            "group_head_id",
            "part_name",
            "part_head_name",
            "part_head_id",
        ]
    )


def _client(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'organization-import.db'}"
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


def test_admin_can_import_organizations_from_csv(tmp_path):
    client = _client(tmp_path)

    try:
        response = client.post(
            "/api/admin/organizations/import",
            files={"file": ("organizations.csv", CSV_TEXT.encode("utf-8"), "text/csv")},
            headers={"X-Employee-Id": "admin001"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["imported_count"] == 1
    assert body["organizations"][0]["part_name"] == "수입파트"
    assert body["organizations"][0]["email_preview"]["part_head_email"] == "impp1@samsung.com"


def test_inputter_cannot_import_organizations_from_csv(tmp_path):
    client = _client(tmp_path)

    try:
        response = client.post(
            "/api/admin/organizations/import",
            files={"file": ("organizations.csv", CSV_TEXT.encode("utf-8"), "text/csv")},
            headers={"X-Employee-Id": "part001"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


def test_csv_import_strips_blank_cells_before_org_type_detection(tmp_path):
    client = _client(tmp_path)
    csv_text = """실명,실장명,실장ID,팀명,팀장명,팀장ID,그룹명,그룹장명,그룹장ID,파트명,파트장명,파트장ID
CSV실,CSV실장,csv-div,CSV팀,CSV팀장,csv-team,   ,   ,   ,CSV직속파트,CSV파트장,csv-part
"""

    try:
        response = client.post(
            "/api/admin/organizations/import",
            files={"file": ("organizations.csv", csv_text.encode("utf-8"), "text/csv")},
            headers={"X-Employee-Id": "admin001"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    organization = response.json()["organizations"][0]
    assert organization["org_type"] == "TEAM_DIRECT"
    assert organization["group_name"] is None
    assert organization["group_head_id"] is None


def test_organization_import_append_mode_keeps_existing_organizations(tmp_path):
    client = _client(tmp_path)

    try:
        first_response = client.post(
            "/api/admin/organizations",
            json={
                "division_name": "기존실",
                "division_head_name": "기존실장",
                "division_head_id": "keep-div",
                "team_name": "기존팀",
                "team_head_name": "기존팀장",
                "team_head_id": "keep-team",
                "group_name": "기존그룹",
                "group_head_name": "기존그룹장",
                "group_head_id": "keep-group",
                "part_name": "기존파트",
                "part_head_name": "기존파트장",
                "part_head_id": "keep-part",
                "org_type": "NORMAL",
            },
            headers={"X-Employee-Id": "admin001"},
        )
        csv_text = "\n".join(
            [
                CSV_HEADER,
                "추가실,추가실장,add-div,추가팀,추가팀장,add-team,추가그룹,추가그룹장,add-group,추가파트,추가파트장,add-part",
            ]
        )
        import_response = client.post(
            "/api/admin/organizations/import?mode=append",
            files={"file": ("organizations.csv", csv_text.encode("utf-8"), "text/csv")},
            headers={"X-Employee-Id": "admin001"},
        )
        listed = client.get("/api/organizations", headers={"X-Employee-Id": "admin001"}).json()

        assert first_response.status_code == 201
        assert import_response.status_code == 201
        assert {"기존파트", "추가파트"}.issubset({org["part_name"] for org in listed})
    finally:
        app.dependency_overrides.clear()


def test_organization_import_replace_mode_removes_unreferenced_stale_organizations(tmp_path):
    client = _client(tmp_path)

    try:
        stale_response = client.post(
            "/api/admin/organizations",
            json={
                "division_name": "삭제실",
                "division_head_name": "삭제실장",
                "division_head_id": "delete-div",
                "team_name": "삭제팀",
                "team_head_name": "삭제팀장",
                "team_head_id": "delete-team",
                "group_name": "삭제그룹",
                "group_head_name": "삭제그룹장",
                "group_head_id": "delete-group",
                "part_name": "삭제대상파트",
                "part_head_name": "삭제파트장",
                "part_head_id": "delete-part",
                "org_type": "NORMAL",
            },
            headers={"X-Employee-Id": "admin001"},
        )
        seed_org = client.get("/api/organizations", headers={"X-Employee-Id": "admin001"}).json()[0]
        csv_text = "\n".join(
            [
                CSV_HEADER,
                _csv_line(seed_org),
                "교체실,교체실장,replace-div,교체팀,교체팀장,replace-team,교체그룹,교체그룹장,replace-group,교체파트,교체파트장,replace-part",
            ]
        )
        import_response = client.post(
            "/api/admin/organizations/import?mode=replace",
            files={"file": ("organizations.csv", csv_text.encode("utf-8"), "text/csv")},
            headers={"X-Employee-Id": "admin001"},
        )
        listed = client.get("/api/organizations", headers={"X-Employee-Id": "admin001"}).json()

        assert stale_response.status_code == 201
        assert import_response.status_code == 201
        part_names = {org["part_name"] for org in listed}
        assert "교체파트" in part_names
        assert "삭제대상파트" not in part_names
    finally:
        app.dependency_overrides.clear()


def test_managed_approver_assigned_to_csv_team_direct_part_keeps_single_org_scope(tmp_path):
    client = _client(tmp_path)
    csv_text = """실명,실장명,실장ID,팀명,팀장명,팀장ID,그룹명,그룹장명,그룹장ID,파트명,파트장명,파트장ID
CSV실,CSV실장,csv-div,CSV팀,CSV팀장,csv-team,   ,   ,   ,CSV직속파트A,CSV파트장A,csv-part-a
CSV실,CSV실장,csv-div,CSV팀,CSV팀장,csv-team,   ,   ,   ,CSV직속파트B,CSV파트장B,csv-part-b
"""

    try:
        import_response = client.post(
            "/api/admin/organizations/import",
            files={"file": ("organizations.csv", csv_text.encode("utf-8"), "text/csv")},
            headers={"X-Employee-Id": "admin001"},
        )
        first_org_id = import_response.json()["organizations"][0]["id"]
        create_user_response = client.post(
            "/api/admin/users",
            headers={"X-Employee-Id": "admin001"},
            json={
                "employee_id": "csv-managed",
                "name": "CSV 관리자",
                "role": "APPROVER",
                "organization_id": first_org_id,
            },
        )
        scope_response = client.get(
            "/api/organizations",
            headers={"X-Employee-Id": "csv-managed"},
        )
    finally:
        app.dependency_overrides.clear()

    assert import_response.status_code == 201
    assert create_user_response.status_code == 201
    assert scope_response.status_code == 200
    assert [organization["part_name"] for organization in scope_response.json()] == ["CSV직속파트A"]


def test_initialize_database_normalizes_existing_imported_organization_whitespace(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'existing-import.db'}"
    initialize_database(database_url=database_url, reset=True)
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    with testing_session() as db:
        org = Organization(
            division_name=" CSV실 ",
            division_head_name=" CSV실장 ",
            division_head_id=" csv-div ",
            team_name=" CSV팀 ",
            team_head_name=" CSV팀장 ",
            team_head_id=" csv-team ",
            group_name="   ",
            group_head_name="   ",
            group_head_id="   ",
            part_name=" CSV직속파트 ",
            part_head_name=" CSV파트장 ",
            part_head_id=" csv-part ",
            org_type="NORMAL",
        )
        db.add(org)
        db.commit()
        org_id = org.id

    initialize_database(database_url=database_url)

    with testing_session() as db:
        org = db.get(Organization, org_id)
        assert org.division_name == "CSV실"
        assert org.group_name is None
        assert org.group_head_id is None
        assert org.part_head_id == "csv-part"
        assert org.org_type == "TEAM_DIRECT"
