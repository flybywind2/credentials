from uuid import uuid4

from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import app
from backend.services import current_user as current_user_module
from backend.services.auth_tokens import verify_access_token


def test_login_maps_part_head_to_inputter_role_and_org():
    client = TestClient(app)

    response = client.post("/api/auth/login", json={"employee_id": "part001"})

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] != "mock-token-part001"
    token_payload = verify_access_token(body["access_token"])
    assert token_payload["employee_id"] == "part001"
    assert body["user"]["employee_id"] == "part001"
    assert body["user"]["role"] == "INPUTTER"
    assert body["user"]["organization"]["part_name"] == "AI전략실행파트"


def test_me_accepts_bearer_token():
    client = TestClient(app)
    login_response = client.post("/api/auth/login", json={"employee_id": "part001"})
    token = login_response.json()["access_token"]

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["employee_id"] == "part001"


def test_me_uses_employee_id_header_when_present():
    client = TestClient(app)

    response = client.get("/api/auth/me", headers={"X-Employee-Id": "group001"})

    assert response.status_code == 200
    body = response.json()
    assert body["employee_id"] == "group001"
    assert body["role"] == "APPROVER"
    assert body["organization"]["group_name"] == "AI실행그룹"


def test_mock_me_uses_employee_id_header_when_bearer_token_is_for_another_user():
    client = TestClient(app)
    login_response = client.post("/api/auth/login", json={"employee_id": "admin001"})
    token = login_response.json()["access_token"]

    response = client.get(
        "/api/auth/me",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Employee-Id": "group001",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["employee_id"] == "group001"
    assert body["role"] == "APPROVER"


def test_broker_me_uses_broker_header_instead_of_dev_header_or_stale_token(monkeypatch):
    client = TestClient(app)
    login_response = client.post("/api/auth/login", json={"employee_id": "admin001"})
    token = login_response.json()["access_token"]
    monkeypatch.setattr(
        current_user_module,
        "settings",
        Settings(sso_mode="broker", sso_broker_employee_header="X-Broker-Employee-Id"),
    )

    response = client.get(
        "/api/auth/me",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Employee-Id": "admin001",
            "X-Broker-Employee-Id": "group001",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["employee_id"] == "group001"
    assert body["role"] == "APPROVER"
    assert body["sso_provider"] == "broker"


def test_broker_me_requires_configured_employee_header(monkeypatch):
    monkeypatch.setattr(
        current_user_module,
        "settings",
        Settings(sso_mode="broker", sso_broker_employee_header="X-Broker-Employee-Id"),
    )
    client = TestClient(app)

    response = client.get(
        "/api/auth/me",
        headers={"X-Employee-Id": "admin001"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Broker employee header is required"


def test_broker_me_maps_unique_deptname_to_imported_part(monkeypatch):
    client = TestClient(app)
    employee_id = f"dept{uuid4().hex[:8]}"
    create_response = client.post(
        "/api/admin/organizations",
        json={
            "division_name": "AI Development Office (AI Center)",
            "division_head_name": "실장",
            "division_head_id": f"{employee_id}-div",
            "team_name": "Generative AI Team (AI Center)",
            "team_head_name": "팀장",
            "team_head_id": f"{employee_id}-team",
            "group_name": "AI/IT Strategy Group (AI Center)",
            "group_head_name": "그룹장",
            "group_head_id": f"{employee_id}-group",
            "part_name": "생성AI전략파트",
            "part_head_name": "파트장",
            "part_head_id": f"{employee_id}-part",
            "org_type": "NORMAL",
        },
        headers={"X-Employee-Id": "admin001"},
    )
    assert create_response.status_code == 201
    org_id = create_response.json()["id"]
    monkeypatch.setattr(
        current_user_module,
        "settings",
        Settings(
            sso_mode="broker",
            sso_broker_employee_header="X-Broker-Employee-Id",
            sso_broker_dept_header="deptname",
        ),
    )

    try:
        response = client.get(
            "/api/auth/me",
            headers={
                "X-Broker-Employee-Id": employee_id,
                "deptname": "AI/IT Strategy Group (AI Center)",
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["employee_id"] == employee_id
        assert body["role"] == "INPUTTER"
        assert body["organization"]["id"] == org_id
        assert body["organization"]["part_name"] == "생성AI전략파트"
    finally:
        monkeypatch.setattr(current_user_module, "settings", Settings())
        client.delete(f"/api/admin/organizations/{org_id}", headers={"X-Employee-Id": "admin001"})


def test_broker_me_requires_registration_when_deptname_has_no_part_match(monkeypatch):
    monkeypatch.setattr(
        current_user_module,
        "settings",
        Settings(
            sso_mode="broker",
            sso_broker_employee_header="X-Broker-Employee-Id",
            sso_broker_dept_header="deptname",
        ),
    )
    client = TestClient(app)

    response = client.get(
        "/api/auth/me",
        headers={
            "X-Broker-Employee-Id": f"dept{uuid4().hex[:8]}",
            "deptname": "Unregistered Group (AI Center)",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "ORG_MAPPING_REQUIRED"
    assert "담당자에게 정보 등록을 요청" in response.json()["detail"]["message"]


def test_login_rejects_unknown_employee_id():
    client = TestClient(app)

    response = client.post("/api/auth/login", json={"employee_id": "missing"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Unknown employee_id"


def test_login_accepts_admin_managed_user():
    client = TestClient(app)
    employee_id = "login-managed-user"

    create_response = client.post(
        "/api/admin/users",
        json={
            "employee_id": employee_id,
            "name": "로그인관리사용자",
            "role": "INPUTTER",
            "organization_id": 1,
        },
        headers={"X-Employee-Id": "admin001"},
    )
    assert create_response.status_code in {201, 400}

    try:
        response = client.post("/api/auth/login", json={"employee_id": employee_id})

        assert response.status_code == 200
        body = response.json()
        assert verify_access_token(body["access_token"])["employee_id"] == employee_id
        assert body["user"]["role"] == "INPUTTER"
    finally:
        client.delete(
            f"/api/admin/users/{employee_id}",
            headers={"X-Employee-Id": "admin001"},
        )


def test_login_maps_group_head_part_head_dual_role_to_approver():
    client = TestClient(app)
    employee_id = f"dual{uuid4().hex[:8]}"
    create_response = client.post(
        "/api/admin/organizations",
        json={
            "division_name": "겸임실",
            "division_head_name": "겸임실장",
            "division_head_id": f"{employee_id}-div",
            "team_name": "겸임팀",
            "team_head_name": "겸임팀장",
            "team_head_id": f"{employee_id}-team",
            "group_name": "겸임그룹",
            "group_head_name": "겸임그룹장",
            "group_head_id": employee_id,
            "part_name": "겸임파트",
            "part_head_name": "겸임파트장",
            "part_head_id": employee_id,
            "org_type": "NORMAL",
        },
        headers={"X-Employee-Id": "admin001"},
    )
    assert create_response.status_code == 201
    org_id = create_response.json()["id"]

    try:
        response = client.post("/api/auth/login", json={"employee_id": employee_id})

        assert response.status_code == 200
        body = response.json()
        assert body["user"]["role"] == "APPROVER"
        assert body["user"]["organization"]["id"] == org_id
    finally:
        client.delete(
            f"/api/admin/organizations/{org_id}",
            headers={"X-Employee-Id": "admin001"},
        )


def test_login_prefers_part_head_org_when_approver_also_heads_a_part():
    client = TestClient(app)
    employee_id = f"dual{uuid4().hex[:8]}"
    group_org_response = client.post(
        "/api/admin/organizations",
        json={
            "division_name": "겸임다중실",
            "division_head_name": "겸임다중실장",
            "division_head_id": f"{employee_id}-div",
            "team_name": "겸임다중팀",
            "team_head_name": "겸임다중팀장",
            "team_head_id": f"{employee_id}-team",
            "group_name": "겸임다중그룹",
            "group_head_name": "겸임다중그룹장",
            "group_head_id": employee_id,
            "part_name": "겸임다중일반파트",
            "part_head_name": "일반파트장",
            "part_head_id": f"{employee_id}a",
            "org_type": "NORMAL",
        },
        headers={"X-Employee-Id": "admin001"},
    )
    own_part_response = client.post(
        "/api/admin/organizations",
        json={
            "division_name": "겸임다중실",
            "division_head_name": "겸임다중실장",
            "division_head_id": f"{employee_id}-div",
            "team_name": "겸임다중팀",
            "team_head_name": "겸임다중팀장",
            "team_head_id": f"{employee_id}-team",
            "group_name": "겸임다중그룹",
            "group_head_name": "겸임다중그룹장",
            "group_head_id": employee_id,
            "part_name": "겸임다중본인파트",
            "part_head_name": "겸임다중파트장",
            "part_head_id": employee_id,
            "org_type": "NORMAL",
        },
        headers={"X-Employee-Id": "admin001"},
    )
    assert group_org_response.status_code == 201
    assert own_part_response.status_code == 201
    group_org_id = group_org_response.json()["id"]
    own_part_org_id = own_part_response.json()["id"]

    try:
        response = client.post("/api/auth/login", json={"employee_id": employee_id})

        assert response.status_code == 200
        body = response.json()
        assert body["user"]["role"] == "APPROVER"
        assert body["user"]["organization"]["id"] == own_part_org_id
    finally:
        for org_id in (own_part_org_id, group_org_id):
            client.delete(
                f"/api/admin/organizations/{org_id}",
                headers={"X-Employee-Id": "admin001"},
            )


def test_saml_acs_issues_token_for_valid_assertion(monkeypatch):
    from backend.routers import auth as auth_router
    from backend.services.sso import AuthenticatedIdentity

    class FakeAdapter:
        def authenticate_response(self, saml_response):
            assert saml_response == "valid-saml"
            return AuthenticatedIdentity(
                employee_id="group001",
                provider="saml",
                attributes={"displayName": "박그룹장"},
            )

    monkeypatch.setattr(auth_router, "get_sso_adapter", lambda: FakeAdapter())
    client = TestClient(app)

    response = client.post("/api/auth/saml/acs", data={"SAMLResponse": "valid-saml"})

    assert response.status_code == 200
    body = response.json()
    assert verify_access_token(body["access_token"])["employee_id"] == "group001"
    assert body["user"]["role"] == "APPROVER"
