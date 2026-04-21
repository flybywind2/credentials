from fastapi.testclient import TestClient

from backend.main import app
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


def test_login_rejects_unknown_employee_id():
    client = TestClient(app)

    response = client.post("/api/auth/login", json={"employee_id": "missing"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Unknown employee_id"


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
