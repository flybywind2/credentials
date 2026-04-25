from fastapi.testclient import TestClient

from backend.main import app
from backend.services.excel import write_workbook


def test_submit_approval_blocks_invalid_confidential_task():
    client = TestClient(app)
    created = client.post(
        "/api/tasks",
        json={
            "organization_id": 1,
            "major_task": "제출 차단 대업무",
            "detail_task": "제출 차단 세부업무",
            "confidential_answers": [["설계자료"]],
        },
        headers={"X-Employee-Id": "part001"},
    ).json()

    response = client.post(
        "/api/approvals/submit?org_id=1",
        headers={"X-Employee-Id": "part001"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Task validation failed"
    assert response.json()["validation_errors"][0]["field"] == "conf_data_type"

    client.delete(f"/api/tasks/{created['id']}", headers={"X-Employee-Id": "part001"})


def test_admin_can_submit_approval_for_valid_div_direct_org():
    client = TestClient(app)
    org = client.post(
        "/api/admin/organizations",
        json={
            "division_name": "승인실",
            "division_head_name": "승인실장",
            "division_head_id": "apd1",
            "part_name": "승인파트",
            "part_head_name": "승인파트장",
            "part_head_id": "app1",
            "org_type": "DIV_DIRECT",
        },
        headers={"X-Employee-Id": "admin001"},
    ).json()
    task = client.post(
        "/api/tasks",
        json={
            "organization_id": org["id"],
            "major_task": "승인 대업무",
            "detail_task": "승인 세부업무",
            "confidential_answers": [["해당 없음"]],
            "national_tech_answers": [["해당 없음"]],
        },
        headers={"X-Employee-Id": "admin001"},
    ).json()

    response = client.post(
        f"/api/approvals/submit?org_id={org['id']}",
        headers={"X-Employee-Id": "admin001"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "PENDING"
    assert body["total_steps"] == 1
    assert body["steps"][0]["approver_employee_id"] == "apd1"

    client.delete(f"/api/tasks/{task['id']}", headers={"X-Employee-Id": "admin001"})
    client.delete(f"/api/admin/organizations/{org['id']}", headers={"X-Employee-Id": "admin001"})


def test_submit_approval_uses_actual_group_and_team_heads_when_division_head_is_missing():
    client = TestClient(app)
    org_response = client.post(
        "/api/admin/organizations",
        json={
            "division_name": "무실장실",
            "team_name": "무실장팀",
            "team_head_name": "실제팀장",
            "team_head_id": "actualteam1",
            "group_name": "무실장그룹",
            "group_head_name": "실제그룹장",
            "group_head_id": "actualgroup1",
            "part_name": "무실장파트",
            "part_head_name": "무실장파트장",
            "part_head_id": "nodivpart1",
            "org_type": "NORMAL",
        },
        headers={"X-Employee-Id": "admin001"},
    )
    assert org_response.status_code == 201
    org = org_response.json()
    task = client.post(
        "/api/tasks",
        json={
            "organization_id": org["id"],
            "major_task": "무실장 대업무",
            "detail_task": "무실장 세부업무",
            "confidential_answers": [["해당 없음"]],
            "national_tech_answers": [["해당 없음"]],
        },
        headers={"X-Employee-Id": "admin001"},
    ).json()

    response = client.post(
        f"/api/approvals/submit?org_id={org['id']}",
        headers={"X-Employee-Id": "admin001"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["total_steps"] == 2
    assert [
        (step["approver_employee_id"], step["approver_name"], step["approver_role"])
        for step in body["steps"]
    ] == [
        ("actualgroup1", "실제그룹장", "그룹장"),
        ("actualteam1", "실제팀장", "팀장"),
    ]

    client.delete(f"/api/tasks/{task['id']}", headers={"X-Employee-Id": "admin001"})
    client.delete(f"/api/admin/organizations/{org['id']}", headers={"X-Employee-Id": "admin001"})


def test_submit_approval_blocks_uploaded_rows_until_web_classification_is_saved():
    client = TestClient(app)
    org = client.post(
        "/api/admin/organizations",
        json={
            "division_name": "업로드실",
            "division_head_name": "업로드실장",
            "division_head_id": "uploaddiv1",
            "part_name": "업로드파트",
            "part_head_name": "업로드파트장",
            "part_head_id": "uploadpart1",
            "org_type": "DIV_DIRECT",
        },
        headers={"X-Employee-Id": "admin001"},
    ).json()
    workbook = write_workbook(
        [
            ["소파트", "대업무", "세부업무"],
            ["업로드", "업로드 대업무", "업로드 세부업무"],
        ],
    )
    imported = client.post(
        f"/api/tasks/import?org_id={org['id']}",
        files={
            "file": (
                "tasks.xlsx",
                workbook,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        headers={"X-Employee-Id": "admin001"},
    ).json()

    response = client.post(
        f"/api/approvals/submit?org_id={org['id']}",
        headers={"X-Employee-Id": "admin001"},
    )

    assert imported["tasks"][0]["status"] == "UPLOADED"
    assert response.status_code == 400
    body = response.json()
    assert body["detail"] == "Task validation failed"
    assert body["validation_errors"][0]["field"] == "status"

    client.delete(f"/api/tasks/{imported['tasks'][0]['id']}", headers={"X-Employee-Id": "admin001"})
    client.delete(f"/api/admin/organizations/{org['id']}", headers={"X-Employee-Id": "admin001"})


def test_resubmission_after_rejection_creates_new_approval_request():
    client = TestClient(app)
    org = client.post(
        "/api/admin/organizations",
        json={
            "division_name": "재제출실",
            "division_head_name": "김실장",
            "division_head_id": "div001",
            "part_name": "재제출파트",
            "part_head_name": "재제출파트장",
            "part_head_id": "resubmit001",
            "org_type": "DIV_DIRECT",
        },
        headers={"X-Employee-Id": "admin001"},
    ).json()
    client.post(
        "/api/tasks",
        json={
            "organization_id": org["id"],
            "major_task": "재제출 대업무",
            "detail_task": "재제출 세부업무",
            "confidential_answers": [["해당 없음"]],
            "national_tech_answers": [["해당 없음"]],
        },
        headers={"X-Employee-Id": "admin001"},
    )
    first = client.post(
        f"/api/approvals/submit?org_id={org['id']}",
        headers={"X-Employee-Id": "admin001"},
    ).json()
    client.post(
        f"/api/approvals/{first['id']}/reject",
        json={"reject_reason": "재제출 테스트 반려"},
        headers={"X-Employee-Id": "div001"},
    )

    second_response = client.post(
        f"/api/approvals/submit?org_id={org['id']}",
        headers={"X-Employee-Id": "admin001"},
    )

    assert second_response.status_code == 201
    second = second_response.json()
    assert second["id"] != first["id"]
    assert second["status"] == "PENDING"
    tasks = client.get(
        f"/api/tasks?org_id={org['id']}",
        headers={"X-Employee-Id": "admin001"},
    ).json()
    assert {task["status"] for task in tasks} == {"SUBMITTED"}
