from uuid import uuid4

from fastapi.testclient import TestClient

from backend.main import app


def _employee_id() -> str:
    return f"perm{uuid4().hex[:8]}"


def test_admin_user_list_includes_seed_org_heads():
    client = TestClient(app)

    response = client.get("/api/admin/users", headers={"X-Employee-Id": "admin001"})

    assert response.status_code == 200
    users = {item["employee_id"]: item for item in response.json()}
    assert users["admin001"]["role"] == "ADMIN"
    assert users["part001"]["role"] == "INPUTTER"
    assert users["group001"]["role"] == "APPROVER"
    assert users["team001"]["role"] == "APPROVER"
    assert users["div001"]["role"] == "APPROVER"


def test_admin_can_create_update_and_delete_user_permission():
    client = TestClient(app)
    employee_id = _employee_id()

    create_response = client.post(
        "/api/admin/users",
        json={
            "employee_id": employee_id,
            "name": "권한테스트",
            "role": "INPUTTER",
            "organization_id": 1,
        },
        headers={"X-Employee-Id": "admin001"},
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["employee_id"] == employee_id
    assert created["organization"]["part_name"] == "AI전략실행파트"

    update_response = client.put(
        f"/api/admin/users/{employee_id}",
        json={"name": "권한수정", "role": "APPROVER", "organization_id": 1},
        headers={"X-Employee-Id": "admin001"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["role"] == "APPROVER"

    me_response = client.get("/api/auth/me", headers={"X-Employee-Id": employee_id})
    assert me_response.status_code == 200
    assert me_response.json()["role"] == "APPROVER"

    delete_response = client.delete(
        f"/api/admin/users/{employee_id}",
        headers={"X-Employee-Id": "admin001"},
    )
    assert delete_response.status_code == 204


def test_inputter_cannot_manage_users():
    client = TestClient(app)

    response = client.get("/api/admin/users", headers={"X-Employee-Id": "part001"})

    assert response.status_code == 403
