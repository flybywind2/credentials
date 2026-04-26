from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete

from backend.database import SessionLocal
from backend.main import app
from backend.models import ApprovalRequest, ApprovalStep


def test_managed_group_approver_sees_assigned_group_pending_request():
    client = TestClient(app)
    admin_headers = {"X-Employee-Id": "admin001"}
    approval_id = None
    suffix = uuid4().hex[:8]
    division_head_id = f"managed-pending-div-{suffix}"
    team_head_id = f"managed-pending-team-{suffix}"
    actual_group_head_id = f"csv-managed-pending-group-{suffix}"
    part_head_id = f"managed-pending-part-{suffix}"
    managed_group_id = f"managed-pending-group-{suffix}"
    org_response = client.post(
        "/api/admin/organizations",
        headers=admin_headers,
        json={
            "division_name": "관리승인실",
            "division_head_name": "관리승인실장",
            "division_head_id": division_head_id,
            "team_name": "관리승인팀",
            "team_head_name": "관리승인팀장",
            "team_head_id": team_head_id,
            "group_name": "관리승인그룹",
            "group_head_name": "CSV그룹장",
            "group_head_id": actual_group_head_id,
            "part_name": "관리승인파트",
            "part_head_name": "관리승인파트장",
            "part_head_id": part_head_id,
            "org_type": "NORMAL",
        },
    )
    assert org_response.status_code == 201
    org = org_response.json()
    task_response = client.post(
        "/api/tasks",
        headers=admin_headers,
        json={
            "organization_id": org["id"],
            "major_task": "관리 승인 대업무",
            "detail_task": "DB 권한관리 지정 그룹장이 승인할 업무",
            "confidential_answers": [["해당 없음"]],
            "national_tech_answers": [["해당 없음"]],
        },
    )
    assert task_response.status_code == 201
    create_user_response = client.post(
        "/api/admin/users",
        headers=admin_headers,
        json={
            "employee_id": managed_group_id,
            "name": "권한관리그룹장",
            "role": "APPROVER",
            "organization_id": org["id"],
        },
    )
    assert create_user_response.status_code == 201
    submit_response = client.post(
        f"/api/approvals/submit?org_id={org['id']}",
        headers={"X-Employee-Id": part_head_id},
    )
    assert submit_response.status_code == 201
    approval_id = submit_response.json()["id"]
    assert submit_response.json()["steps"][0]["approver_employee_id"] == actual_group_head_id

    try:
        status_response = client.get(
            "/api/approvals/subordinate-status",
            headers={"X-Employee-Id": managed_group_id},
        )
        pending_response = client.get(
            "/api/approvals/pending",
            headers={"X-Employee-Id": managed_group_id},
        )
        history_response = client.get(
            f"/api/approvals/{approval_id}/history",
            headers={"X-Employee-Id": managed_group_id},
        )
        approve_response = client.post(
            f"/api/approvals/{approval_id}/approve",
            headers={"X-Employee-Id": managed_group_id},
        )

        assert status_response.status_code == 200
        assert any(row["approval_status"] == "PENDING" for row in status_response.json()["rows"])
        assert pending_response.status_code == 200
        assert approval_id in {item["id"] for item in pending_response.json()}
        assert history_response.status_code == 200
        assert history_response.json()["id"] == approval_id
        assert approve_response.status_code == 200
        assert approve_response.json()["current_step"] == 2
    finally:
        if approval_id is not None:
            with SessionLocal() as db:
                db.execute(delete(ApprovalStep).where(ApprovalStep.approval_request_id == approval_id))
                db.execute(delete(ApprovalRequest).where(ApprovalRequest.id == approval_id))
                db.commit()
        client.delete(f"/api/admin/users/{managed_group_id}", headers=admin_headers)
        client.delete(f"/api/tasks/{task_response.json()['id']}", headers=admin_headers)
        client.delete(f"/api/admin/organizations/{org['id']}", headers=admin_headers)


def test_pending_approvals_are_filtered_by_current_approver():
    client = TestClient(app)

    response = client.get("/api/approvals/pending", headers={"X-Employee-Id": "group001"})

    assert response.status_code == 200
    body = response.json()
    assert body
    assert {item["current_approver_employee_id"] for item in body} == {"group001"}
    assert "requested_at" in body[0]
    assert body[0]["part_name"] == "AI전략기획파트"


def test_current_team_approver_can_read_tasks_for_assigned_approval_even_when_team_name_differs():
    client = TestClient(app)
    admin_headers = {"X-Employee-Id": "admin001"}
    approval_id = None
    suffix = uuid4().hex[:8]
    org_response = client.post(
        "/api/admin/organizations",
        headers=admin_headers,
        json={
            "division_name": f"팀승인실-{suffix}",
            "division_head_name": "팀승인실장",
            "division_head_id": f"team-approval-div-{suffix}",
            "team_name": f"팀승인팀-{suffix}",
            "team_head_name": "팀승인팀장",
            "team_head_id": "team001",
            "part_name": f"팀승인파트-{suffix}",
            "part_head_name": "팀승인파트장",
            "part_head_id": f"team-approval-part-{suffix}",
            "org_type": "TEAM_DIRECT",
        },
    )
    assert org_response.status_code == 201
    org = org_response.json()
    task_response = client.post(
        "/api/tasks",
        headers=admin_headers,
        json={
            "organization_id": org["id"],
            "major_task": "팀장 승인 대업무",
            "detail_task": "현재 승인자인 팀장이 상세 업무를 조회해야 한다.",
            "confidential_answers": [["해당 없음"]],
            "national_tech_answers": [["해당 없음"]],
        },
    )
    assert task_response.status_code == 201
    submit_response = client.post(
        f"/api/approvals/submit?org_id={org['id']}",
        headers=admin_headers,
    )
    assert submit_response.status_code == 201
    approval_id = submit_response.json()["id"]
    assert submit_response.json()["steps"][0]["approver_employee_id"] == "team001"

    try:
        pending_response = client.get("/api/approvals/pending", headers={"X-Employee-Id": "team001"})
        tasks_response = client.get(f"/api/tasks?org_id={org['id']}", headers={"X-Employee-Id": "team001"})

        assert approval_id in {item["id"] for item in pending_response.json()}
        assert tasks_response.status_code == 200
        assert task_response.json()["id"] in {item["id"] for item in tasks_response.json()}
    finally:
        if approval_id is not None:
            with SessionLocal() as db:
                db.execute(delete(ApprovalStep).where(ApprovalStep.approval_request_id == approval_id))
                db.execute(delete(ApprovalRequest).where(ApprovalRequest.id == approval_id))
                db.commit()
        client.delete(f"/api/tasks/{task_response.json()['id']}", headers=admin_headers)
        client.delete(f"/api/admin/organizations/{org['id']}", headers=admin_headers)


def test_current_division_approver_can_read_tasks_for_assigned_approval_even_when_division_name_differs():
    client = TestClient(app)
    admin_headers = {"X-Employee-Id": "admin001"}
    approval_id = None
    suffix = uuid4().hex[:8]
    org_response = client.post(
        "/api/admin/organizations",
        headers=admin_headers,
        json={
            "division_name": f"실승인실-{suffix}",
            "division_head_name": "실승인실장",
            "division_head_id": "div001",
            "part_name": f"실승인파트-{suffix}",
            "part_head_name": "실승인파트장",
            "part_head_id": f"div-approval-part-{suffix}",
            "org_type": "DIV_DIRECT",
        },
    )
    assert org_response.status_code == 201
    org = org_response.json()
    task_response = client.post(
        "/api/tasks",
        headers=admin_headers,
        json={
            "organization_id": org["id"],
            "major_task": "실장 승인 대업무",
            "detail_task": "현재 승인자인 실장이 상세 업무를 조회해야 한다.",
            "confidential_answers": [["해당 없음"]],
            "national_tech_answers": [["해당 없음"]],
        },
    )
    assert task_response.status_code == 201
    submit_response = client.post(
        f"/api/approvals/submit?org_id={org['id']}",
        headers=admin_headers,
    )
    assert submit_response.status_code == 201
    approval_id = submit_response.json()["id"]
    assert submit_response.json()["steps"][0]["approver_employee_id"] == "div001"

    try:
        pending_response = client.get("/api/approvals/pending", headers={"X-Employee-Id": "div001"})
        tasks_response = client.get(f"/api/tasks?org_id={org['id']}", headers={"X-Employee-Id": "div001"})

        assert approval_id in {item["id"] for item in pending_response.json()}
        assert tasks_response.status_code == 200
        assert task_response.json()["id"] in {item["id"] for item in tasks_response.json()}
    finally:
        if approval_id is not None:
            with SessionLocal() as db:
                db.execute(delete(ApprovalStep).where(ApprovalStep.approval_request_id == approval_id))
                db.execute(delete(ApprovalRequest).where(ApprovalRequest.id == approval_id))
                db.commit()
        client.delete(f"/api/tasks/{task_response.json()['id']}", headers=admin_headers)
        client.delete(f"/api/admin/organizations/{org['id']}", headers=admin_headers)


def test_admin_can_see_pending_approvals_from_database():
    client = TestClient(app)

    response = client.get("/api/approvals/pending", headers={"X-Employee-Id": "admin001"})

    assert response.status_code == 200
    assert any(item["status"] == "PENDING" for item in response.json())
