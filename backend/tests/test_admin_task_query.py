from fastapi.testclient import TestClient

from backend.main import app


def test_admin_can_filter_all_tasks_by_org_and_classification():
    client = TestClient(app)

    response = client.get(
        "/api/admin/tasks?part=AI전략&status=SUBMITTED&is_confidential=true",
        headers={"X-Employee-Id": "admin001"},
    )

    assert response.status_code == 200
    rows = response.json()["items"]
    assert rows
    assert all(row["part_name"].startswith("AI전략") for row in rows)
    assert all(row["status"] == "SUBMITTED" for row in rows)
    assert all(row["is_confidential"] is True for row in rows)


def test_inputter_can_read_own_part_status_summary():
    client = TestClient(app)

    response = client.get(
        "/api/tasks/status",
        headers={"X-Employee-Id": "part001"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["organization_id"] == 1
    assert "DRAFT" in body["status_counts"]


def test_part_status_summary_counts_classification_applicable_ratio():
    client = TestClient(app)
    org = client.post(
        "/api/admin/organizations",
        json={
            "division_name": "비율실",
            "division_head_name": "비율실장",
            "division_head_id": "ratio-div",
            "team_name": "비율팀",
            "team_head_name": "비율팀장",
            "team_head_id": "ratio-team",
            "group_name": "비율그룹",
            "group_head_name": "비율그룹장",
            "group_head_id": "ratio-group",
            "part_name": "비율파트",
            "part_head_name": "비율파트장",
            "part_head_id": "ratio-part",
            "org_type": "NORMAL",
        },
        headers={"X-Employee-Id": "admin001"},
    ).json()
    applicable = client.post(
        "/api/tasks",
        json={
            "organization_id": org["id"],
            "major_task": "해당 대업무",
            "detail_task": "해당 세부업무",
            "confidential_answers": [["해당 됨"]],
            "national_tech_answers": [["해당 없음"]],
        },
        headers={"X-Employee-Id": "admin001"},
    ).json()
    not_applicable = client.post(
        "/api/tasks",
        json={
            "organization_id": org["id"],
            "major_task": "미해당 대업무",
            "detail_task": "미해당 세부업무",
            "confidential_answers": [["해당 없음"]],
            "national_tech_answers": [["해당 없음"]],
        },
        headers={"X-Employee-Id": "admin001"},
    ).json()

    try:
        response = client.get(
            f"/api/tasks/status?org_id={org['id']}",
            headers={"X-Employee-Id": "admin001"},
        )

        assert response.status_code == 200
        assert response.json()["classification_summary"] == {
            "total": 2,
            "applicable": 1,
            "not_applicable": 1,
        }
    finally:
        client.delete(f"/api/tasks/{applicable['id']}", headers={"X-Employee-Id": "admin001"})
        client.delete(f"/api/tasks/{not_applicable['id']}", headers={"X-Employee-Id": "admin001"})
        client.delete(f"/api/admin/organizations/{org['id']}", headers={"X-Employee-Id": "admin001"})
