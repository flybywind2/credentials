from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import get_db
from backend.main import app
from backend.scripts.init_db import initialize_database


def _client(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'approval-status.db'}"
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


def _create_org(
    client: TestClient,
    *,
    division_name: str,
    division_head_id: str,
    team_name: str | None,
    team_head_id: str | None,
    group_name: str | None,
    group_head_id: str | None,
    part_name: str,
    part_head_id: str,
    org_type: str = "NORMAL",
) -> int:
    response = client.post(
        "/api/admin/organizations",
        headers={"X-Employee-Id": "admin001"},
        json={
            "division_name": division_name,
            "division_head_name": f"{division_name}장",
            "division_head_id": division_head_id,
            "team_name": team_name,
            "team_head_name": f"{team_name}장" if team_name else None,
            "team_head_id": team_head_id,
            "group_name": group_name,
            "group_head_name": f"{group_name}장" if group_name else None,
            "group_head_id": group_head_id,
            "part_name": part_name,
            "part_head_name": f"{part_name}장",
            "part_head_id": part_head_id,
            "org_type": org_type,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_task(client: TestClient, org_id: int, label: str, employee_id: str = "admin001") -> int:
    response = client.post(
        "/api/tasks",
        headers={"X-Employee-Id": employee_id},
        json={
            "organization_id": org_id,
            "major_task": f"{label} 대업무",
            "detail_task": f"{label} 세부업무",
            "confidential_answers": [["해당 없음"]],
            "national_tech_answers": [["해당 없음"]],
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_group_head_subordinate_status_shows_part_rows_and_approval_state(tmp_path):
    client = _client(tmp_path)

    try:
        first_org_id = _create_org(
            client,
            division_name="요약실",
            division_head_id="summary-div",
            team_name="요약팀",
            team_head_id="summary-team",
            group_name="요약그룹",
            group_head_id="summary-group",
            part_name="요약파트A",
            part_head_id="summary-part-a",
        )
        second_org_id = _create_org(
            client,
            division_name="요약실",
            division_head_id="summary-div",
            team_name="요약팀",
            team_head_id="summary-team",
            group_name="요약그룹",
            group_head_id="summary-group",
            part_name="요약파트B",
            part_head_id="summary-part-b",
        )
        _create_task(client, first_org_id, "승인대기", employee_id="summary-part-a")
        _create_task(client, second_org_id, "미요청", employee_id="summary-part-b")
        submit_response = client.post(
            f"/api/approvals/submit?org_id={first_org_id}",
            headers={"X-Employee-Id": "summary-part-a"},
        )
        assert submit_response.status_code == 201

        response = client.get(
            "/api/approvals/subordinate-status",
            headers={"X-Employee-Id": "summary-group"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["scope_label"] == "파트현황"
        rows_by_name = {row["display_name"]: row for row in body["rows"]}
        assert rows_by_name["요약파트A"]["unit_type"] == "PART"
        assert rows_by_name["요약파트A"]["approval_status"] == "PENDING"
        assert rows_by_name["요약파트A"]["approval_status_label"] == "승인대기"
        assert rows_by_name["요약파트B"]["approval_status"] == "NOT_REQUESTED"
        assert rows_by_name["요약파트B"]["status_counts"]["DRAFT"] == 1
    finally:
        app.dependency_overrides.clear()


def test_team_head_status_groups_groups_and_expands_team_direct_parts(tmp_path):
    client = _client(tmp_path)

    try:
        normal_org_id = _create_org(
            client,
            division_name="팀요약실",
            division_head_id="team-summary-div",
            team_name="팀요약팀",
            team_head_id="team-summary",
            group_name="팀요약그룹",
            group_head_id="team-summary-group",
            part_name="팀요약파트",
            part_head_id="team-summary-part",
        )
        direct_org_id = _create_org(
            client,
            division_name="팀요약실",
            division_head_id="team-summary-div",
            team_name="팀요약팀",
            team_head_id="team-summary",
            group_name=None,
            group_head_id=None,
            part_name="팀직속파트",
            part_head_id="team-direct-part",
            org_type="TEAM_DIRECT",
        )
        _create_task(client, normal_org_id, "그룹집계", employee_id="team-summary-part")
        _create_task(client, direct_org_id, "직속파트", employee_id="team-direct-part")

        response = client.get(
            "/api/approvals/subordinate-status",
            headers={"X-Employee-Id": "team-summary"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["scope_label"] == "그룹현황"
        rows_by_name = {row["display_name"]: row for row in body["rows"]}
        assert rows_by_name["팀요약그룹"]["unit_type"] == "GROUP"
        assert rows_by_name["팀요약그룹"]["task_count"] == 1
        assert rows_by_name["팀직속파트"]["unit_type"] == "PART"
        assert rows_by_name["팀직속파트"]["task_count"] == 1
    finally:
        app.dependency_overrides.clear()


def test_managed_team_head_status_uses_team_scope_not_assigned_group(tmp_path):
    client = _client(tmp_path)

    try:
        first_group_org_id = _create_org(
            client,
            division_name="관리팀요약실",
            division_head_id="managed-team-summary-div",
            team_name="관리팀요약팀",
            team_head_id="managed-team-summary",
            group_name="관리팀요약그룹A",
            group_head_id="managed-team-summary-group-a",
            part_name="관리팀요약파트A",
            part_head_id="managed-team-summary-part-a",
        )
        second_group_org_id = _create_org(
            client,
            division_name="관리팀요약실",
            division_head_id="managed-team-summary-div",
            team_name="관리팀요약팀",
            team_head_id="managed-team-summary",
            group_name="관리팀요약그룹B",
            group_head_id="managed-team-summary-group-b",
            part_name="관리팀요약파트B",
            part_head_id="managed-team-summary-part-b",
        )
        direct_org_id = _create_org(
            client,
            division_name="관리팀요약실",
            division_head_id="managed-team-summary-div",
            team_name="관리팀요약팀",
            team_head_id="managed-team-summary",
            group_name=None,
            group_head_id=None,
            part_name="관리팀직속파트",
            part_head_id="managed-team-summary-direct-part",
            org_type="TEAM_DIRECT",
        )
        create_user_response = client.post(
            "/api/admin/users",
            headers={"X-Employee-Id": "admin001"},
            json={
                "employee_id": "managed-team-summary",
                "name": "관리팀요약팀장",
                "role": "APPROVER",
                "organization_id": first_group_org_id,
            },
        )
        assert create_user_response.status_code == 201
        _create_task(client, first_group_org_id, "관리그룹A", employee_id="managed-team-summary-part-a")
        _create_task(client, second_group_org_id, "관리그룹B", employee_id="managed-team-summary-part-b")
        _create_task(client, direct_org_id, "관리직속", employee_id="managed-team-summary-direct-part")

        response = client.get(
            "/api/approvals/subordinate-status",
            headers={"X-Employee-Id": "managed-team-summary"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["scope_label"] == "그룹현황"
        rows_by_name = {row["display_name"]: row for row in body["rows"]}
        assert rows_by_name["관리팀요약그룹A"]["unit_type"] == "GROUP"
        assert rows_by_name["관리팀요약그룹B"]["unit_type"] == "GROUP"
        assert rows_by_name["관리팀직속파트"]["unit_type"] == "PART"
    finally:
        app.dependency_overrides.clear()


def test_division_head_status_shows_team_rows_and_expands_division_direct_parts(tmp_path):
    client = _client(tmp_path)

    try:
        team_org_id = _create_org(
            client,
            division_name="실요약실",
            division_head_id="division-summary",
            team_name="실요약팀",
            team_head_id="division-summary-team",
            group_name="실요약그룹",
            group_head_id="division-summary-group",
            part_name="실요약파트",
            part_head_id="division-summary-part",
        )
        direct_org_id = _create_org(
            client,
            division_name="실요약실",
            division_head_id="division-summary",
            team_name=None,
            team_head_id=None,
            group_name=None,
            group_head_id=None,
            part_name="실직속파트",
            part_head_id="division-direct-part",
            org_type="DIV_DIRECT",
        )
        _create_task(client, team_org_id, "팀집계", employee_id="division-summary-part")
        _create_task(client, direct_org_id, "실직속", employee_id="division-direct-part")

        response = client.get(
            "/api/approvals/subordinate-status",
            headers={"X-Employee-Id": "division-summary"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["scope_label"] == "실현황"
        rows_by_name = {row["display_name"]: row for row in body["rows"]}
        assert rows_by_name["실요약팀"]["unit_type"] == "TEAM"
        assert rows_by_name["실요약팀"]["task_count"] == 1
        assert rows_by_name["실직속파트"]["unit_type"] == "PART"
        assert rows_by_name["실직속파트"]["task_count"] == 1
    finally:
        app.dependency_overrides.clear()
