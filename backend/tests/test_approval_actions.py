from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.database import SessionLocal
from backend.main import app
from backend.models import ApprovalRequest, ApprovalStep


def _unique_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


def _create_div_direct_submission(client: TestClient, part_name: str) -> dict:
    suffix = uuid4().hex[:8]
    org = client.post(
        "/api/admin/organizations",
        json={
            "division_name": f"처리실-{suffix}",
            "division_head_name": "김실장",
            "division_head_id": "div001",
            "part_name": f"{part_name}-{suffix}",
            "part_head_name": "처리파트장",
            "part_head_id": _unique_id("part"),
            "org_type": "DIV_DIRECT",
        },
        headers={"X-Employee-Id": "admin001"},
    ).json()
    task = client.post(
        "/api/tasks",
        json={
            "organization_id": org["id"],
            "major_task": "처리 대업무",
            "detail_task": "처리 세부업무",
            "confidential_answers": [["해당 없음"]],
            "national_tech_answers": [["해당 없음"]],
        },
        headers={"X-Employee-Id": "admin001"},
    ).json()
    approval = client.post(
        f"/api/approvals/submit?org_id={org['id']}",
        headers={"X-Employee-Id": "admin001"},
    ).json()
    return {"org": org, "task": task, "approval": approval}


def test_current_approver_can_approve_final_step():
    client = TestClient(app)
    data = _create_div_direct_submission(client, "승인처리파트")

    response = client.post(
        f"/api/approvals/{data['approval']['id']}/approve",
        headers={"X-Employee-Id": "div001"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "APPROVED"
    assert body["steps"][0]["status"] == "APPROVED"


def test_current_approver_can_reject_with_reason():
    client = TestClient(app)
    data = _create_div_direct_submission(client, "반려처리파트")

    response = client.post(
        f"/api/approvals/{data['approval']['id']}/reject",
        json={"reject_reason": "분류 근거 보완 필요"},
        headers={"X-Employee-Id": "div001"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "REJECTED"
    assert body["reject_reason"] == "분류 근거 보완 필요"


def test_reject_requires_reason():
    client = TestClient(app)
    data = _create_div_direct_submission(client, "반려사유필수파트")

    response = client.post(
        f"/api/approvals/{data['approval']['id']}/reject",
        json={"reject_reason": ""},
        headers={"X-Employee-Id": "div001"},
    )

    assert response.status_code == 422


def test_requester_can_cancel_pending_request_and_submit_again():
    client = TestClient(app)
    data = _create_div_direct_submission(client, "취소처리파트")
    approval_id = data["approval"]["id"]

    cancel_response = client.post(
        f"/api/approvals/{approval_id}/cancel",
        headers={"X-Employee-Id": "admin001"},
    )
    status_response = client.get(
        f"/api/tasks/status?org_id={data['org']['id']}",
        headers={"X-Employee-Id": "admin001"},
    )
    tasks_after_cancel = client.get(
        f"/api/tasks?org_id={data['org']['id']}",
        headers={"X-Employee-Id": "admin001"},
    ).json()
    resubmit_response = client.post(
        f"/api/approvals/submit?org_id={data['org']['id']}",
        headers={"X-Employee-Id": "admin001"},
    )

    assert cancel_response.status_code == 200
    cancelled = cancel_response.json()
    assert cancelled["status"] == "CANCELLED"
    assert {step["status"] for step in cancelled["steps"]} == {"CANCELLED"}
    assert {task["status"] for task in tasks_after_cancel} == {"DRAFT"}
    assert status_response.json()["approval_status"] == "CANCELLED"
    assert status_response.json()["active_approval_id"] is None
    assert resubmit_response.status_code == 201
    assert resubmit_response.json()["status"] == "PENDING"


def test_part_status_exposes_cancel_permission_only_to_requester_or_admin():
    client = TestClient(app)
    data = _create_div_direct_submission(client, "취소권한표시파트")
    viewer_id = _unique_id("viewer")
    create_viewer_response = client.post(
        "/api/admin/users",
        json={
            "employee_id": viewer_id,
            "name": "취소권한조회자",
            "role": "APPROVER",
            "organization_id": data["org"]["id"],
        },
        headers={"X-Employee-Id": "admin001"},
    )
    assert create_viewer_response.status_code == 201

    try:
        admin_status = client.get(
            f"/api/tasks/status?org_id={data['org']['id']}",
            headers={"X-Employee-Id": "admin001"},
        )
        approver_status = client.get(
            f"/api/tasks/status?org_id={data['org']['id']}",
            headers={"X-Employee-Id": viewer_id},
        )

        assert admin_status.status_code == 200
        assert admin_status.json()["approval_status"] == "PENDING"
        assert admin_status.json()["can_cancel_approval"] is True
        assert approver_status.status_code == 200
        assert approver_status.json()["approval_status"] == "PENDING"
        assert approver_status.json()["can_cancel_approval"] is False
    finally:
        client.delete(f"/api/admin/users/{viewer_id}", headers={"X-Employee-Id": "admin001"})


def test_cancel_keeps_tasks_submitted_when_duplicate_pending_request_remains():
    client = TestClient(app)
    data = _create_div_direct_submission(client, "중복요청취소파트")
    first_approval_id = data["approval"]["id"]

    with SessionLocal() as db:
        first = db.get(ApprovalRequest, first_approval_id)
        duplicate = ApprovalRequest(
            organization_id=first.organization_id,
            requested_by=first.requested_by,
            status="PENDING",
            current_step=first.current_step,
            total_steps=first.total_steps,
        )
        db.add(duplicate)
        db.flush()
        first_steps = db.scalars(
            select(ApprovalStep)
            .where(ApprovalStep.approval_request_id == first_approval_id)
            .order_by(ApprovalStep.step_order)
        ).all()
        for step in first_steps:
            db.add(
                ApprovalStep(
                    approval_request_id=duplicate.id,
                    step_order=step.step_order,
                    approver_employee_id=step.approver_employee_id,
                    approver_name=step.approver_name,
                    approver_role=step.approver_role,
                    status="PENDING",
                )
            )
        db.commit()
        duplicate_approval_id = duplicate.id

    first_cancel = client.post(
        f"/api/approvals/{first_approval_id}/cancel",
        headers={"X-Employee-Id": "admin001"},
    )
    tasks_after_first_cancel = client.get(
        f"/api/tasks?org_id={data['org']['id']}",
        headers={"X-Employee-Id": "admin001"},
    ).json()
    second_cancel = client.post(
        f"/api/approvals/{duplicate_approval_id}/cancel",
        headers={"X-Employee-Id": "admin001"},
    )
    tasks_after_second_cancel = client.get(
        f"/api/tasks?org_id={data['org']['id']}",
        headers={"X-Employee-Id": "admin001"},
    ).json()

    assert first_cancel.status_code == 200
    assert {task["status"] for task in tasks_after_first_cancel} == {"SUBMITTED"}
    assert second_cancel.status_code == 200
    assert {task["status"] for task in tasks_after_second_cancel} == {"DRAFT"}


def test_submit_blocks_duplicate_pending_request():
    client = TestClient(app)
    data = _create_div_direct_submission(client, "중복요청차단파트")

    duplicate_response = client.post(
        f"/api/approvals/submit?org_id={data['org']['id']}",
        headers={"X-Employee-Id": "admin001"},
    )

    assert duplicate_response.status_code == 400
    assert duplicate_response.json()["detail"] == "Pending approval request already exists"


def test_requester_can_cancel_started_approval_and_submit_again():
    client = TestClient(app)
    suffix = uuid4().hex[:8]
    group_head_id = _unique_id("cgroup")
    part_head_id = _unique_id("cancel-part")
    org = client.post(
        "/api/admin/organizations",
        json={
            "division_name": f"취소차단실-{suffix}",
            "division_head_name": "취소차단실장",
            "division_head_id": _unique_id("cancel-div"),
            "team_name": f"취소차단팀-{suffix}",
            "team_head_name": "취소차단팀장",
            "team_head_id": _unique_id("cancel-team"),
            "group_name": f"취소차단그룹-{suffix}",
            "group_head_name": "취소차단그룹장",
            "group_head_id": group_head_id,
            "part_name": f"취소차단파트-{suffix}",
            "part_head_name": "취소차단파트장",
            "part_head_id": part_head_id,
            "org_type": "NORMAL",
        },
        headers={"X-Employee-Id": "admin001"},
    ).json()
    client.post(
        "/api/tasks",
        json={
            "organization_id": org["id"],
            "major_task": "취소 차단 대업무",
            "detail_task": "1단계 승인 후 취소 차단",
            "confidential_answers": [["해당 없음"]],
            "national_tech_answers": [["해당 없음"]],
        },
        headers={"X-Employee-Id": part_head_id},
    )
    approval = client.post(
        f"/api/approvals/submit?org_id={org['id']}",
        headers={"X-Employee-Id": part_head_id},
    ).json()
    approve_response = client.post(
        f"/api/approvals/{approval['id']}/approve",
        headers={"X-Employee-Id": group_head_id},
    )
    status_before_cancel = client.get(
        f"/api/tasks/status?org_id={org['id']}",
        headers={"X-Employee-Id": part_head_id},
    )

    cancel_response = client.post(
        f"/api/approvals/{approval['id']}/cancel",
        headers={"X-Employee-Id": part_head_id},
    )
    status_after_cancel = client.get(
        f"/api/tasks/status?org_id={org['id']}",
        headers={"X-Employee-Id": part_head_id},
    )
    tasks_after_cancel = client.get(
        f"/api/tasks?org_id={org['id']}",
        headers={"X-Employee-Id": part_head_id},
    ).json()
    resubmit_response = client.post(
        f"/api/approvals/submit?org_id={org['id']}",
        headers={"X-Employee-Id": part_head_id},
    )

    assert approve_response.status_code == 200
    assert status_before_cancel.status_code == 200
    assert status_before_cancel.json()["can_cancel_approval"] is True
    assert cancel_response.status_code == 200
    cancelled = cancel_response.json()
    assert cancelled["status"] == "CANCELLED"
    assert cancelled["steps"][0]["status"] == "APPROVED"
    assert {step["status"] for step in cancelled["steps"][1:]} == {"CANCELLED"}
    assert status_after_cancel.status_code == 200
    assert status_after_cancel.json()["approval_status"] == "CANCELLED"
    assert status_after_cancel.json()["active_approval_id"] is None
    assert {task["status"] for task in tasks_after_cancel} == {"DRAFT"}
    assert resubmit_response.status_code == 201
    assert resubmit_response.json()["status"] == "PENDING"
