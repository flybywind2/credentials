from fastapi.testclient import TestClient

from backend.main import app


def test_inputter_cannot_read_same_group_org_tasks():
    client = TestClient(app)
    org = client.post(
        "/api/admin/organizations",
        json={
            "division_name": "AI전략실",
            "division_head_name": "김실장",
            "division_head_id": "div001",
            "team_name": "AI전략팀",
            "team_head_name": "이팀장",
            "team_head_id": "team001",
            "group_name": "AI실행그룹",
            "group_head_name": "박그룹장",
            "group_head_id": "group001",
            "part_name": "동일그룹파트",
            "part_head_name": "다른파트장",
            "part_head_id": "samegrp001",
            "org_type": "NORMAL",
        },
        headers={"X-Employee-Id": "admin001"},
    ).json()
    client.post(
        "/api/tasks",
        json={
            "organization_id": org["id"],
            "major_task": "동일 그룹 대업무",
            "detail_task": "동일 그룹 세부업무",
        },
        headers={"X-Employee-Id": "admin001"},
    )

    direct_read_response = client.get(
        f"/api/tasks?org_id={org['id']}",
        headers={"X-Employee-Id": "part001"},
    )
    list_response = client.get("/api/tasks", headers={"X-Employee-Id": "part001"})
    group_response = client.get("/api/tasks/group", headers={"X-Employee-Id": "part001"})
    write_response = client.post(
        "/api/tasks",
        json={
            "organization_id": org["id"],
            "major_task": "권한 없는 작성",
            "detail_task": "권한 없는 작성",
        },
        headers={"X-Employee-Id": "part001"},
    )

    assert direct_read_response.status_code == 403
    assert org["id"] not in {row["organization_id"] for row in list_response.json()}
    assert group_response.status_code == 403
    assert write_response.status_code == 403
