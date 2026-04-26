from fastapi.testclient import TestClient

from backend.main import app


def _create_div_direct_submission(client: TestClient, suffix: str) -> tuple[dict, dict, dict]:
    org = client.post(
        "/api/admin/organizations",
        json={
            "division_name": f"검토실{suffix}",
            "division_head_name": "검토실장",
            "division_head_id": "div001",
            "part_name": f"검토파트{suffix}",
            "part_head_name": "검토파트장",
            "part_head_id": f"reviewer{suffix}",
            "org_type": "DIV_DIRECT",
        },
        headers={"X-Employee-Id": "admin001"},
    ).json()
    task = client.post(
        "/api/tasks",
        json={
            "organization_id": org["id"],
            "major_task": f"검토 대업무 {suffix}",
            "detail_task": f"검토 세부업무 {suffix}",
            "confidential_answers": [["해당 없음"]],
            "national_tech_answers": [["해당 없음"]],
        },
        headers={"X-Employee-Id": "admin001"},
    ).json()
    approval = client.post(
        f"/api/approvals/submit?org_id={org['id']}",
        headers={"X-Employee-Id": "admin001"},
    ).json()
    return org, task, approval


def test_approve_request_records_per_task_review_decision_and_comment():
    client = TestClient(app)
    org, task, approval = _create_div_direct_submission(client, "approve")

    try:
        response = client.post(
            f"/api/approvals/{approval['id']}/approve",
            json={
                "task_reviews": [
                    {
                        "task_id": task["id"],
                        "decision": "APPROVED",
                        "comment": "분류 기준 확인 완료",
                    }
                ]
            },
            headers={"X-Employee-Id": "div001"},
        )

        assert response.status_code == 200
        history = client.get(
            f"/api/approvals/{approval['id']}/history",
            headers={"X-Employee-Id": "div001"},
        ).json()
        assert history["task_reviews"] == [
            {
                "task_id": task["id"],
                "major_task": task["major_task"],
                "decision": "APPROVED",
                "comment": "분류 기준 확인 완료",
                "reviewer_employee_id": "div001",
            }
        ]
    finally:
        client.delete(f"/api/tasks/{task['id']}", headers={"X-Employee-Id": "admin001"})
        client.delete(f"/api/admin/organizations/{org['id']}", headers={"X-Employee-Id": "admin001"})


def test_reject_request_requires_rejected_task_comment_when_reviews_are_submitted():
    client = TestClient(app)
    org, task, approval = _create_div_direct_submission(client, "reject")

    try:
        response = client.post(
            f"/api/approvals/{approval['id']}/reject",
            json={
                "reject_reason": "항목 검토 반려",
                "task_reviews": [
                    {"task_id": task["id"], "decision": "REJECTED", "comment": ""}
                ],
            },
            headers={"X-Employee-Id": "div001"},
        )

        assert response.status_code == 400
        assert "comment" in response.json()["detail"]
    finally:
        client.delete(f"/api/tasks/{task['id']}", headers={"X-Employee-Id": "admin001"})
        client.delete(f"/api/admin/organizations/{org['id']}", headers={"X-Employee-Id": "admin001"})


def test_latest_rejection_exposes_per_task_review_comments_to_inputter():
    client = TestClient(app)
    org, task, approval = _create_div_direct_submission(client, "inputterview")

    try:
        reject = client.post(
            f"/api/approvals/{approval['id']}/reject",
            json={
                "reject_reason": "항목별 검토 반려",
                "task_reviews": [
                    {
                        "task_id": task["id"],
                        "decision": "REJECTED",
                        "comment": "기밀 판단 근거 보완",
                    }
                ],
            },
            headers={"X-Employee-Id": "div001"},
        )
        assert reject.status_code == 200

        response = client.get(
            f"/api/tasks/rejection?org_id={org['id']}",
            headers={"X-Employee-Id": "admin001"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["has_rejection"] is True
        assert body["task_reviews"] == [
            {
                "task_id": task["id"],
                "major_task": task["major_task"],
                "decision": "REJECTED",
                "comment": "기밀 판단 근거 보완",
                "reviewer_employee_id": "div001",
            }
        ]
    finally:
        client.delete(f"/api/tasks/{task['id']}", headers={"X-Employee-Id": "admin001"})
        client.delete(f"/api/admin/organizations/{org['id']}", headers={"X-Employee-Id": "admin001"})


def test_partial_task_rejection_keeps_approved_items_submitted():
    client = TestClient(app)
    org = client.post(
        "/api/admin/organizations",
        json={
            "division_name": "검토실partial",
            "division_head_name": "검토실장",
            "division_head_id": "div001",
            "part_name": "검토파트partial",
            "part_head_name": "검토파트장",
            "part_head_id": "reviewerpartial",
            "org_type": "DIV_DIRECT",
        },
        headers={"X-Employee-Id": "admin001"},
    ).json()
    rejected_task = client.post(
        "/api/tasks",
        json={
            "organization_id": org["id"],
            "major_task": "반려 대상 대업무",
            "detail_task": "보완 필요한 세부업무",
            "confidential_answers": [["해당 없음"]],
            "national_tech_answers": [["해당 없음"]],
        },
        headers={"X-Employee-Id": "admin001"},
    ).json()
    approved_task = client.post(
        "/api/tasks",
        json={
            "organization_id": org["id"],
            "major_task": "승인 유지 대업무",
            "detail_task": "반려 없이 유지될 세부업무",
            "confidential_answers": [["해당 없음"]],
            "national_tech_answers": [["해당 없음"]],
        },
        headers={"X-Employee-Id": "admin001"},
    ).json()
    approval = client.post(
        f"/api/approvals/submit?org_id={org['id']}",
        headers={"X-Employee-Id": "admin001"},
    ).json()

    try:
        reject = client.post(
            f"/api/approvals/{approval['id']}/reject",
            json={
                "reject_reason": "일부 항목만 반려",
                "task_reviews": [
                    {
                        "task_id": rejected_task["id"],
                        "decision": "REJECTED",
                        "comment": "이 항목만 보완",
                    },
                    {
                        "task_id": approved_task["id"],
                        "decision": "APPROVED",
                        "comment": "문제 없음",
                    },
                ],
            },
            headers={"X-Employee-Id": "div001"},
        )
        tasks = client.get(
            f"/api/tasks?org_id={org['id']}",
            headers={"X-Employee-Id": "admin001"},
        ).json()

        assert reject.status_code == 200
        statuses_by_id = {task["id"]: task["status"] for task in tasks}
        assert statuses_by_id[rejected_task["id"]] == "REJECTED"
        assert statuses_by_id[approved_task["id"]] == "SUBMITTED"
    finally:
        client.delete(f"/api/tasks/{approved_task['id']}", headers={"X-Employee-Id": "admin001"})
        client.delete(f"/api/tasks/{rejected_task['id']}", headers={"X-Employee-Id": "admin001"})
        client.delete(f"/api/admin/organizations/{org['id']}", headers={"X-Employee-Id": "admin001"})


def test_admin_task_query_exposes_latest_task_review():
    client = TestClient(app)
    org, task, approval = _create_div_direct_submission(client, "adminview")

    try:
        reject = client.post(
            f"/api/approvals/{approval['id']}/reject",
            json={
                "reject_reason": "관리자 조회 반려",
                "task_reviews": [
                    {
                        "task_id": task["id"],
                        "decision": "REJECTED",
                        "comment": "관리자 화면 표시 의견",
                    }
                ],
            },
            headers={"X-Employee-Id": "div001"},
        )
        assert reject.status_code == 200

        response = client.get(
            f"/api/admin/tasks?part={org['part_name']}",
            headers={"X-Employee-Id": "admin001"},
        )

        assert response.status_code == 200
        item = response.json()["items"][0]
        assert item["latest_review"] == {
            "decision": "REJECTED",
            "comment": "관리자 화면 표시 의견",
            "reviewer_employee_id": "div001",
            "approval_id": approval["id"],
        }
    finally:
        client.delete(f"/api/tasks/{task['id']}", headers={"X-Employee-Id": "admin001"})
        client.delete(f"/api/admin/organizations/{org['id']}", headers={"X-Employee-Id": "admin001"})
