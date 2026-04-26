from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from backend.database import get_db
from backend.main import app
from backend.models import (
    ApprovalRequest,
    ConfidentialQuestion,
    NationalTechQuestion,
    Organization,
    TaskEntry,
    User,
)
from backend.scripts.seed_demo_data import seed_demo_data


def _demo_client(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'demo-scenarios.db'}"
    seed_demo_data(database_url)
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), testing_session


def _part_names(response) -> set[str]:
    assert response.status_code == 200
    return {item["part_name"] for item in response.json()}


def _approval_part_names(response) -> set[str]:
    assert response.status_code == 200
    return {item["part_name"] for item in response.json()}


def _status_rows_by_name(response) -> dict[str, dict]:
    assert response.status_code == 200
    return {row["display_name"]: row for row in response.json()["rows"]}


def test_demo_seed_contract_has_expected_accounts_counts_and_fixed_options(tmp_path):
    client, testing_session = _demo_client(tmp_path)

    try:
        with testing_session() as db:
            assert db.scalar(select(func.count(Organization.id))) == 12
            assert db.scalar(select(func.count(User.id))) == 23
            assert db.scalar(select(func.count(TaskEntry.id))) == 28
            assert db.scalar(select(func.count(ApprovalRequest.id))) == 10
            expected_users = {
                "part002": "INPUTTER",
                "part003": "INPUTTER",
                "part004": "INPUTTER",
                "group002": "APPROVER",
                "team002": "APPROVER",
            }
            for employee_id, role in expected_users.items():
                user = db.scalar(select(User).where(User.employee_id == employee_id))
                assert user is not None
                assert user.role == role
            confidential = db.scalar(select(ConfidentialQuestion))
            national = db.scalar(select(NationalTechQuestion))
            assert confidential.options == ["해당 없음", "해당 됨"]
            assert national.options == ["해당 없음", "해당 됨"]

        assert client.get("/api/health").status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_demo_inputter_scope_is_limited_to_own_part(tmp_path):
    client, _ = _demo_client(tmp_path)

    try:
        me_response = client.get("/api/auth/me", headers={"X-Employee-Id": "part002"})
        assert me_response.status_code == 200
        assert me_response.json()["role"] == "INPUTTER"
        assert me_response.json()["organization"]["part_name"] == "업무자동화파트"

        orgs_response = client.get("/api/organizations", headers={"X-Employee-Id": "part002"})
        assert _part_names(orgs_response) == {"업무자동화파트"}

        tasks_response = client.get("/api/tasks", headers={"X-Employee-Id": "part002"})
        assert tasks_response.status_code == 200
        tasks = tasks_response.json()
        assert len(tasks) == 3
        assert {task["organization_id"] for task in tasks} == {2}

        off_scope_response = client.get(
            "/api/tasks?org_id=1",
            headers={"X-Employee-Id": "part002"},
        )
        assert off_scope_response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_demo_group_approver_scope_and_pending_status(tmp_path):
    client, _ = _demo_client(tmp_path)

    try:
        group001_orgs = client.get("/api/organizations", headers={"X-Employee-Id": "group001"})
        assert _part_names(group001_orgs) == {
            "AI전략기획파트",
            "업무자동화파트",
            "데이터플랫폼파트",
        }
        group001_status = client.get(
            "/api/approvals/subordinate-status",
            headers={"X-Employee-Id": "group001"},
        )
        assert group001_status.json()["scope_label"] == "파트현황"
        group001_rows = _status_rows_by_name(group001_status)
        assert group001_rows["AI전략기획파트"]["approval_status"] == "PENDING"
        assert group001_rows["업무자동화파트"]["approval_status"] == "PENDING"
        assert group001_rows["업무자동화파트"]["current_step"] == 2
        assert group001_rows["데이터플랫폼파트"]["approval_status"] == "APPROVED"
        group001_pending = client.get("/api/approvals/pending", headers={"X-Employee-Id": "group001"})
        assert _approval_part_names(group001_pending) == {"AI전략기획파트"}

        group002_orgs = client.get("/api/organizations", headers={"X-Employee-Id": "group002"})
        assert _part_names(group002_orgs) == {"DX프로세스파트", "현업지원파트"}
        group002_status = client.get(
            "/api/approvals/subordinate-status",
            headers={"X-Employee-Id": "group002"},
        )
        group002_rows = _status_rows_by_name(group002_status)
        assert group002_rows["DX프로세스파트"]["approval_status"] == "PENDING"
        assert group002_rows["현업지원파트"]["approval_status"] == "REJECTED"
        group002_pending = client.get("/api/approvals/pending", headers={"X-Employee-Id": "group002"})
        assert _approval_part_names(group002_pending) == {"DX프로세스파트"}

        off_scope_response = client.get(
            "/api/tasks?org_id=1",
            headers={"X-Employee-Id": "group002"},
        )
        assert off_scope_response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_demo_team_approver_scope_groups_groups_and_direct_parts(tmp_path):
    client, _ = _demo_client(tmp_path)

    try:
        team001_orgs = client.get("/api/organizations", headers={"X-Employee-Id": "team001"})
        assert _part_names(team001_orgs) == {
            "AI전략기획파트",
            "업무자동화파트",
            "데이터플랫폼파트",
            "DX프로세스파트",
            "현업지원파트",
            "정보전략팀 직속기획파트",
        }
        team001_status = client.get(
            "/api/approvals/subordinate-status",
            headers={"X-Employee-Id": "team001"},
        )
        assert team001_status.json()["scope_label"] == "그룹현황"
        team001_rows = _status_rows_by_name(team001_status)
        assert team001_rows["AI/IT전략그룹"]["unit_type"] == "GROUP"
        assert team001_rows["DX기획그룹"]["unit_type"] == "GROUP"
        assert team001_rows["정보전략팀 직속기획파트"]["unit_type"] == "PART"
        team001_pending = client.get("/api/approvals/pending", headers={"X-Employee-Id": "team001"})
        assert _approval_part_names(team001_pending) == {"업무자동화파트", "정보전략팀 직속기획파트"}

        team002_orgs = client.get("/api/organizations", headers={"X-Employee-Id": "team002"})
        assert _part_names(team002_orgs) == {"플랫폼운영파트", "프롬프트검증파트", "업무봇파트"}
        team002_status = client.get(
            "/api/approvals/subordinate-status",
            headers={"X-Employee-Id": "team002"},
        )
        assert team002_status.json()["scope_label"] == "그룹현황"
        team002_rows = _status_rows_by_name(team002_status)
        assert team002_rows["GenAI플랫폼그룹"]["unit_type"] == "GROUP"
        assert team002_rows["LLM서비스그룹"]["unit_type"] == "GROUP"
        team002_pending = client.get("/api/approvals/pending", headers={"X-Employee-Id": "team002"})
        assert team002_pending.status_code == 200
        assert team002_pending.json() == []
    finally:
        app.dependency_overrides.clear()


def test_demo_division_and_admin_scope_cover_direct_parts_and_all_data(tmp_path):
    client, _ = _demo_client(tmp_path)

    try:
        div001_status = client.get(
            "/api/approvals/subordinate-status",
            headers={"X-Employee-Id": "div001"},
        )
        assert div001_status.json()["scope_label"] == "실현황"
        div001_rows = _status_rows_by_name(div001_status)
        assert div001_rows["정보전략팀"]["unit_type"] == "TEAM"
        assert div001_rows["Generative AI팀"]["unit_type"] == "TEAM"
        assert div001_rows["AI개발실 직속혁신파트"]["unit_type"] == "PART"
        div001_pending = client.get("/api/approvals/pending", headers={"X-Employee-Id": "div001"})
        assert _approval_part_names(div001_pending) == {"AI개발실 직속혁신파트"}

        admin_orgs = client.get("/api/organizations", headers={"X-Employee-Id": "admin001"})
        assert admin_orgs.status_code == 200
        assert len(admin_orgs.json()) == 12
        admin_status = client.get(
            "/api/approvals/subordinate-status",
            headers={"X-Employee-Id": "admin001"},
        )
        assert admin_status.status_code == 200
        assert admin_status.json()["scope_label"] == "전체현황"
        assert len(admin_status.json()["rows"]) == 12
    finally:
        app.dependency_overrides.clear()
