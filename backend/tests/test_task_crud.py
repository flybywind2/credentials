from fastapi.testclient import TestClient

from backend.main import app


def test_inputter_can_create_update_and_delete_own_org_task():
    client = TestClient(app)

    create_response = client.post(
        "/api/tasks",
        json={
            "organization_id": 1,
            "sub_part": "테스트",
            "major_task": "신규 대업무",
            "detail_task": "신규 세부업무",
            "storage_location": "테스트 저장소",
            "related_menu": "테스트 메뉴",
            "share_scope": "ORG_UNIT",
        },
        headers={"X-Employee-Id": "part001"},
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["status"] == "DRAFT"
    assert created["created_by_employee_id"] == "part001"

    update_response = client.put(
        f"/api/tasks/{created['id']}",
        json={"major_task": "수정 대업무"},
        headers={"X-Employee-Id": "part001"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["major_task"] == "수정 대업무"

    delete_response = client.delete(
        f"/api/tasks/{created['id']}",
        headers={"X-Employee-Id": "part001"},
    )
    assert delete_response.status_code == 204


def test_inputter_cannot_create_task_for_other_org():
    client = TestClient(app)

    response = client.post(
        "/api/tasks",
        json={
            "organization_id": 999,
            "major_task": "권한 없는 대업무",
            "detail_task": "권한 없는 세부업무",
        },
        headers={"X-Employee-Id": "part001"},
    )

    assert response.status_code == 403


def test_bulk_task_create_uses_same_permissions_and_returns_created_rows():
    client = TestClient(app)

    response = client.post(
        "/api/tasks/bulk",
        json=[
            {
                "organization_id": 1,
                "sub_part": "일괄",
                "major_task": "일괄 대업무 1",
                "detail_task": "일괄 세부업무 1",
                "confidential_answers": [["해당 없음"]],
                "national_tech_answers": [["해당 없음"]],
            },
            {
                "organization_id": 1,
                "sub_part": "일괄",
                "major_task": "일괄 대업무 2",
                "detail_task": "일괄 세부업무 2",
                "confidential_answers": [["해당 없음"]],
                "national_tech_answers": [["해당 없음"]],
            },
        ],
        headers={"X-Employee-Id": "part001"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["created_count"] == 2
    assert [task["major_task"] for task in body["tasks"]] == ["일괄 대업무 1", "일괄 대업무 2"]

    for task in body["tasks"]:
        client.delete(f"/api/tasks/{task['id']}", headers={"X-Employee-Id": "part001"})


def test_inputter_cannot_delete_task_created_by_another_user_in_own_org():
    client = TestClient(app)
    created = client.post(
        "/api/tasks",
        json={
            "organization_id": 1,
            "major_task": "타인 작성 대업무",
            "detail_task": "타인 작성 세부업무",
            "confidential_answers": [["해당 없음"]],
            "national_tech_answers": [["해당 없음"]],
        },
        headers={"X-Employee-Id": "admin001"},
    ).json()

    try:
        response = client.delete(
            f"/api/tasks/{created['id']}",
            headers={"X-Employee-Id": "part001"},
        )

        assert response.status_code == 403
        tasks = client.get("/api/tasks?org_id=1", headers={"X-Employee-Id": "admin001"}).json()
        assert any(task["id"] == created["id"] for task in tasks)
    finally:
        client.delete(f"/api/tasks/{created['id']}", headers={"X-Employee-Id": "admin001"})


def test_create_task_persists_full_detail_form_fields_and_question_answers():
    client = TestClient(app)

    response = client.post(
        "/api/tasks",
        json={
            "organization_id": 1,
            "sub_part": "상세",
            "major_task": "상세 대업무",
            "detail_task": "상세 세부업무",
            "confidential_answers": [
                {"question_id": 1, "selected_options": ["설계 자료"]}
            ],
            "conf_data_type": "설계 문서",
            "conf_owner_user": "OWNER",
            "national_tech_answers": [
                {"question_id": 1, "selected_options": ["해당 없음"]}
            ],
            "ntech_data_type": "",
            "ntech_owner_user": "",
            "is_compliance": True,
            "comp_data_type": "계약 정보",
            "comp_owner_user": "USER",
            "storage_location": "사내 저장소",
            "related_menu": "상세 메뉴",
            "share_scope": "ORG_UNIT",
        },
        headers={"X-Employee-Id": "part001"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["is_confidential"] is True
    assert body["conf_data_type"] == "설계 문서"
    assert body["conf_owner_user"] == "OWNER"
    assert body["is_national_tech"] is False
    assert body["national_tech_answers"] == [
        {"question_id": 1, "selected_options": ["해당 없음"]}
    ]
    assert body["is_compliance"] is True
    assert body["comp_data_type"] == "계약 정보"
    assert body["comp_owner_user"] == "USER"
    assert body["confidential_answers"] == [
        {"question_id": 1, "selected_options": ["설계 자료"]}
    ]

    client.delete(f"/api/tasks/{body['id']}", headers={"X-Employee-Id": "part001"})


def test_update_task_persists_full_detail_form_fields():
    client = TestClient(app)
    created = client.post(
        "/api/tasks",
        json={
            "organization_id": 1,
            "major_task": "상세 수정 전 대업무",
            "detail_task": "상세 수정 전 세부업무",
            "confidential_answers": [["해당 없음"]],
            "national_tech_answers": [["해당 없음"]],
        },
        headers={"X-Employee-Id": "part001"},
    ).json()

    response = client.put(
        f"/api/tasks/{created['id']}",
        json={
            "confidential_answers": [
                {"question_id": 1, "selected_options": ["해당 없음"]}
            ],
            "national_tech_answers": [
                {"question_id": 1, "selected_options": ["반도체 공정"]}
            ],
            "ntech_data_type": "공정 조건",
            "ntech_owner_user": "OWNER",
            "is_compliance": True,
            "comp_data_type": "규제 검토 자료",
            "comp_owner_user": "USER",
        },
        headers={"X-Employee-Id": "part001"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["is_national_tech"] is True
    assert body["national_tech_answers"] == [
        {"question_id": 1, "selected_options": ["반도체 공정"]}
    ]
    assert body["ntech_data_type"] == "공정 조건"
    assert body["ntech_owner_user"] == "OWNER"
    assert body["is_compliance"] is True
    assert body["comp_data_type"] == "규제 검토 자료"
    assert body["comp_owner_user"] == "USER"

    client.delete(f"/api/tasks/{created['id']}", headers={"X-Employee-Id": "part001"})
