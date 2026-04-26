from fastapi.testclient import TestClient

from backend.main import app


def test_public_input_examples_returns_default_rows():
    client = TestClient(app)

    response = client.get("/api/input-examples", headers={"X-Employee-Id": "part001"})

    assert response.status_code == 200
    rows = response.json()
    assert rows
    assert {"sub_part", "major_task", "detail_task"}.issubset(rows[0])


def test_admin_can_replace_input_examples_and_public_reads_them():
    client = TestClient(app)
    original = client.get(
        "/api/admin/input-examples",
        headers={"X-Employee-Id": "admin001"},
    ).json()
    replacement = [
        {
            "sub_part": "예시파트",
            "major_task": "예시 대업무",
            "detail_task": "예시 세부업무",
            "is_confidential": True,
            "is_national_tech": False,
            "is_compliance": True,
            "storage_location": "예시 보관 장소",
            "related_menu": "예시 메뉴",
            "share_scope": "DIVISION_BU",
        }
    ]

    try:
        update_response = client.put(
            "/api/admin/input-examples",
            json={"rows": replacement},
            headers={"X-Employee-Id": "admin001"},
        )
        public_response = client.get("/api/input-examples", headers={"X-Employee-Id": "part001"})

        assert update_response.status_code == 200
        assert update_response.json() == replacement
        assert public_response.json() == replacement
    finally:
        client.put(
            "/api/admin/input-examples",
            json={"rows": original},
            headers={"X-Employee-Id": "admin001"},
        )


def test_inputter_cannot_update_input_examples():
    client = TestClient(app)

    response = client.put(
        "/api/admin/input-examples",
        json={"rows": []},
        headers={"X-Employee-Id": "part001"},
    )

    assert response.status_code == 403
