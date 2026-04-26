from uuid import uuid4

from fastapi.testclient import TestClient

from backend.main import app


def _create_test_org(
    client: TestClient,
    label: str,
    group_head_id: str,
    part_head_id: str,
    group_name: str | None = None,
) -> int:
    response = client.post(
        "/api/admin/organizations",
        json={
            "division_name": f"{label}실",
            "division_head_name": f"{label}실장",
            "division_head_id": f"{part_head_id}-div",
            "team_name": f"{label}팀",
            "team_head_name": f"{label}팀장",
            "team_head_id": f"{part_head_id}-team",
            "group_name": group_name or f"{label}그룹",
            "group_head_name": f"{label}그룹장",
            "group_head_id": group_head_id,
            "part_name": f"{label}파트",
            "part_head_name": f"{label}파트장",
            "part_head_id": part_head_id,
            "org_type": "NORMAL",
        },
        headers={"X-Employee-Id": "admin001"},
    )
    assert response.status_code == 201
    return response.json()["id"]


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


def test_group_head_part_head_dual_role_can_create_own_part_task():
    client = TestClient(app)
    employee_id = f"dual{uuid4().hex[:8]}"
    org_response = client.post(
        "/api/admin/organizations",
        json={
            "division_name": "겸임입력실",
            "division_head_name": "겸임입력실장",
            "division_head_id": f"{employee_id}-div",
            "team_name": "겸임입력팀",
            "team_head_name": "겸임입력팀장",
            "team_head_id": f"{employee_id}-team",
            "group_name": "겸임입력그룹",
            "group_head_name": "겸임입력그룹장",
            "group_head_id": employee_id,
            "part_name": "겸임입력파트",
            "part_head_name": "겸임입력파트장",
            "part_head_id": employee_id,
            "org_type": "NORMAL",
        },
        headers={"X-Employee-Id": "admin001"},
    )
    assert org_response.status_code == 201
    org_id = org_response.json()["id"]
    created_task_id = None

    try:
        me_response = client.get("/api/auth/me", headers={"X-Employee-Id": employee_id})
        assert me_response.status_code == 200
        assert me_response.json()["role"] == "APPROVER"

        response = client.post(
            "/api/tasks",
            json={
                "organization_id": org_id,
                "sub_part": "겸임",
                "major_task": "겸임자가 입력한 대업무",
                "detail_task": "그룹장 겸 파트장 입력 권한 검증",
                "confidential_answers": [["해당 없음"]],
                "national_tech_answers": [["해당 없음"]],
            },
            headers={"X-Employee-Id": employee_id},
        )

        assert response.status_code == 201
        body = response.json()
        created_task_id = body["id"]
        assert body["created_by_employee_id"] == employee_id
    finally:
        if created_task_id is not None:
            client.delete(
                f"/api/tasks/{created_task_id}",
                headers={"X-Employee-Id": employee_id},
            )
        client.delete(
            f"/api/admin/organizations/{org_id}",
            headers={"X-Employee-Id": "admin001"},
        )


def test_group_head_can_update_subordinate_part_task():
    client = TestClient(app)
    group_head_id = f"grp{uuid4().hex[:8]}"
    part_head_id = f"part{uuid4().hex[:8]}"
    org_response = client.post(
        "/api/admin/organizations",
        json={
            "division_name": "하위수정실",
            "division_head_name": "하위수정실장",
            "division_head_id": f"{group_head_id}-div",
            "team_name": "하위수정팀",
            "team_head_name": "하위수정팀장",
            "team_head_id": f"{group_head_id}-team",
            "group_name": "하위수정그룹",
            "group_head_name": "하위수정그룹장",
            "group_head_id": group_head_id,
            "part_name": "하위수정파트",
            "part_head_name": "하위수정파트장",
            "part_head_id": part_head_id,
            "org_type": "NORMAL",
        },
        headers={"X-Employee-Id": "admin001"},
    )
    assert org_response.status_code == 201
    org_id = org_response.json()["id"]
    task_id = None

    try:
        create_response = client.post(
            "/api/tasks",
            json={
                "organization_id": org_id,
                "sub_part": "하위",
                "major_task": "하위 파트 원본 대업무",
                "detail_task": "하위 파트 원본 세부업무",
                "confidential_answers": [["해당 없음"]],
                "national_tech_answers": [["해당 없음"]],
            },
            headers={"X-Employee-Id": part_head_id},
        )
        assert create_response.status_code == 201
        task_id = create_response.json()["id"]

        update_response = client.put(
            f"/api/tasks/{task_id}",
            json={"major_task": "그룹장이 수정한 대업무"},
            headers={"X-Employee-Id": group_head_id},
        )

        assert update_response.status_code == 200
        assert update_response.json()["major_task"] == "그룹장이 수정한 대업무"
    finally:
        if task_id is not None:
            client.delete(f"/api/tasks/{task_id}", headers={"X-Employee-Id": "admin001"})
        client.delete(
            f"/api/admin/organizations/{org_id}",
            headers={"X-Employee-Id": "admin001"},
        )


def test_group_head_can_validate_subordinate_part_task_rows():
    client = TestClient(app)
    group_head_id = f"grp{uuid4().hex[:8]}"
    part_head_id = f"part{uuid4().hex[:8]}"
    org_response = client.post(
        "/api/admin/organizations",
        json={
            "division_name": "하위검증실",
            "division_head_name": "하위검증실장",
            "division_head_id": f"{group_head_id}-div",
            "team_name": "하위검증팀",
            "team_head_name": "하위검증팀장",
            "team_head_id": f"{group_head_id}-team",
            "group_name": "하위검증그룹",
            "group_head_name": "하위검증그룹장",
            "group_head_id": group_head_id,
            "part_name": "하위검증파트",
            "part_head_name": "하위검증파트장",
            "part_head_id": part_head_id,
            "org_type": "NORMAL",
        },
        headers={"X-Employee-Id": "admin001"},
    )
    assert org_response.status_code == 201
    org_id = org_response.json()["id"]

    try:
        response = client.post(
            "/api/tasks/validate",
            json={
                "rows": [
                    {
                        "organization_id": org_id,
                        "major_task": "하위 파트 검증 대업무",
                        "detail_task": "하위 파트 검증 세부업무",
                        "confidential_answers": [["해당 없음"]],
                        "national_tech_answers": [["해당 없음"]],
                    }
                ]
            },
            headers={"X-Employee-Id": group_head_id},
        )

        assert response.status_code == 200
        assert response.json()["errors"] == []
    finally:
        client.delete(
            f"/api/admin/organizations/{org_id}",
            headers={"X-Employee-Id": "admin001"},
        )


def test_group_head_can_update_non_default_subordinate_part_task():
    client = TestClient(app)
    group_head_id = f"grp{uuid4().hex[:8]}"
    base_org_id = _create_test_org(
        client,
        "하위기본",
        group_head_id=group_head_id,
        part_head_id=f"base{uuid4().hex[:8]}",
        group_name="하위공통그룹",
    )
    target_part_head_id = f"target{uuid4().hex[:8]}"
    target_org_id = _create_test_org(
        client,
        "하위대상",
        group_head_id=group_head_id,
        part_head_id=target_part_head_id,
        group_name="하위공통그룹",
    )
    task_id = None

    try:
        me_response = client.get("/api/auth/me", headers={"X-Employee-Id": group_head_id})
        assert me_response.status_code == 200
        assert me_response.json()["organization_id"] == base_org_id
        assert target_org_id != base_org_id

        create_response = client.post(
            "/api/tasks",
            json={
                "organization_id": target_org_id,
                "sub_part": "하위대상",
                "major_task": "대상 파트 원본 대업무",
                "detail_task": "대상 파트 원본 세부업무",
                "confidential_answers": [["해당 없음"]],
                "national_tech_answers": [["해당 없음"]],
            },
            headers={"X-Employee-Id": target_part_head_id},
        )
        assert create_response.status_code == 201
        task_id = create_response.json()["id"]

        update_response = client.put(
            f"/api/tasks/{task_id}",
            json={"major_task": "그룹장이 선택 파트에서 수정한 대업무"},
            headers={"X-Employee-Id": group_head_id},
        )

        assert update_response.status_code == 200
        assert update_response.json()["major_task"] == "그룹장이 선택 파트에서 수정한 대업무"
    finally:
        if task_id is not None:
            client.delete(f"/api/tasks/{task_id}", headers={"X-Employee-Id": "admin001"})
        for org_id in (target_org_id, base_org_id):
            client.delete(
                f"/api/admin/organizations/{org_id}",
                headers={"X-Employee-Id": "admin001"},
            )


def test_group_head_can_validate_non_default_subordinate_part_task_rows():
    client = TestClient(app)
    group_head_id = f"grp{uuid4().hex[:8]}"
    base_org_id = _create_test_org(
        client,
        "하위검증기본",
        group_head_id=group_head_id,
        part_head_id=f"base{uuid4().hex[:8]}",
        group_name="하위검증공통그룹",
    )
    target_org_id = _create_test_org(
        client,
        "하위검증대상",
        group_head_id=group_head_id,
        part_head_id=f"target{uuid4().hex[:8]}",
        group_name="하위검증공통그룹",
    )

    try:
        me_response = client.get("/api/auth/me", headers={"X-Employee-Id": group_head_id})
        assert me_response.status_code == 200
        assert me_response.json()["organization_id"] == base_org_id
        assert target_org_id != base_org_id

        response = client.post(
            "/api/tasks/validate",
            json={
                "rows": [
                    {
                        "organization_id": target_org_id,
                        "major_task": "선택 하위 파트 검증 대업무",
                        "detail_task": "선택 하위 파트 검증 세부업무",
                        "confidential_answers": [["해당 없음"]],
                        "national_tech_answers": [["해당 없음"]],
                    }
                ]
            },
            headers={"X-Employee-Id": group_head_id},
        )

        assert response.status_code == 200
        assert response.json()["errors"] == []
    finally:
        for org_id in (target_org_id, base_org_id):
            client.delete(
                f"/api/admin/organizations/{org_id}",
                headers={"X-Employee-Id": "admin001"},
            )


def test_approver_can_create_non_default_part_head_org_task():
    client = TestClient(app)
    employee_id = f"dual{uuid4().hex[:8]}"
    base_org_id = _create_test_org(
        client,
        "겸임기본",
        group_head_id=employee_id,
        part_head_id=employee_id,
    )
    target_org_id = _create_test_org(
        client,
        "겸임추가",
        group_head_id=f"other{uuid4().hex[:8]}",
        part_head_id=employee_id,
    )
    task_id = None

    try:
        me_response = client.get("/api/auth/me", headers={"X-Employee-Id": employee_id})
        assert me_response.status_code == 200
        assert me_response.json()["role"] == "APPROVER"
        assert me_response.json()["organization_id"] == base_org_id
        assert target_org_id != base_org_id

        response = client.post(
            "/api/tasks",
            json={
                "organization_id": target_org_id,
                "sub_part": "겸임추가",
                "major_task": "겸임 추가 파트 대업무",
                "detail_task": "겸임 추가 파트 세부업무",
                "confidential_answers": [["해당 없음"]],
                "national_tech_answers": [["해당 없음"]],
            },
            headers={"X-Employee-Id": employee_id},
        )

        assert response.status_code == 201
        task_id = response.json()["id"]
        assert response.json()["organization_id"] == target_org_id
    finally:
        if task_id is not None:
            client.delete(f"/api/tasks/{task_id}", headers={"X-Employee-Id": "admin001"})
        for org_id in (target_org_id, base_org_id):
            client.delete(
                f"/api/admin/organizations/{org_id}",
                headers={"X-Employee-Id": "admin001"},
            )


def test_create_task_accepts_blank_optional_form_fields():
    client = TestClient(app)

    response = client.post(
        "/api/tasks",
        json={
            "organization_id": 1,
            "sub_part": "",
            "major_task": "선택값 없는 대업무",
            "detail_task": "선택값 없는 세부업무",
            "confidential_answers": [
                {"question_id": 1, "selected_options": ["해당 없음"]}
            ],
            "conf_data_type": "",
            "conf_owner_user": "",
            "national_tech_answers": [
                {"question_id": 1, "selected_options": ["해당 없음"]}
            ],
            "ntech_data_type": "",
            "ntech_owner_user": "",
            "is_compliance": False,
            "comp_data_type": "",
            "comp_owner_user": "",
            "storage_location": "",
            "related_menu": "",
            "share_scope": "",
        },
        headers={"X-Employee-Id": "part001"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["share_scope"] is None
    assert body["is_confidential"] is False
    assert body["is_national_tech"] is False

    client.delete(f"/api/tasks/{body['id']}", headers={"X-Employee-Id": "part001"})


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
    assert {task["status"] for task in body["tasks"]} == {"UPLOADED"}

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
