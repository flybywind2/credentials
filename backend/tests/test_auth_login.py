from fastapi.testclient import TestClient

from backend.main import app


def test_login_maps_part_head_to_inputter_role_and_org():
    client = TestClient(app)

    response = client.post("/api/auth/login", json={"employee_id": "part001"})

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] == "mock-token-part001"
    assert body["user"]["employee_id"] == "part001"
    assert body["user"]["role"] == "INPUTTER"
    assert body["user"]["organization"]["part_name"] == "AI전략실행파트"


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
