from fastapi.testclient import TestClient

from backend.main import app
from backend.services.excel import parse_workbook, write_workbook


def test_task_template_downloads_excel_headers():
    client = TestClient(app)

    response = client.get("/api/tasks/template", headers={"X-Employee-Id": "part001"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    rows = parse_workbook(response.content)
    assert rows[0] == ["소파트", "대업무", "세부업무"]


def test_task_excel_import_creates_rows():
    client = TestClient(app)
    workbook = write_workbook(
        [
            ["소파트", "대업무", "세부업무"],
            ["엑셀", "엑셀 대업무", "엑셀 세부업무"],
        ],
    )

    response = client.post(
        "/api/tasks/import",
        files={
            "file": (
                "tasks.xlsx",
                workbook,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        headers={"X-Employee-Id": "part001"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["imported_count"] == 1
    assert body["tasks"][0]["major_task"] == "엑셀 대업무"
    assert body["tasks"][0]["status"] == "UPLOADED"
    assert body["tasks"][0]["confidential_answers"] == []
    assert body["tasks"][0]["national_tech_answers"] == []
    assert body["tasks"][0]["is_compliance"] is False


def test_task_excel_import_preview_validates_without_creating_rows():
    client = TestClient(app)
    before_count = len(client.get("/api/tasks", headers={"X-Employee-Id": "part001"}).json())
    workbook = write_workbook(
        [
            ["소파트", "대업무", "세부업무"],
            ["엑셀", "", "세부업무만 있음"],
        ],
    )

    response = client.post(
        "/api/tasks/import/preview",
        files={
            "file": (
                "tasks.xlsx",
                workbook,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        headers={"X-Employee-Id": "part001"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] == 1
    assert body["valid_count"] == 0
    assert body["error_count"] >= 1
    assert body["rows"][0]["detail_task"] == "세부업무만 있음"
    assert len(client.get("/api/tasks", headers={"X-Employee-Id": "part001"}).json()) == before_count


def test_web_update_converts_uploaded_task_to_draft():
    client = TestClient(app)
    workbook = write_workbook(
        [
            ["소파트", "대업무", "세부업무"],
            ["엑셀", "웹분류 대업무", "웹분류 세부업무"],
        ],
    )
    imported = client.post(
        "/api/tasks/import",
        files={
            "file": (
                "tasks.xlsx",
                workbook,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        headers={"X-Employee-Id": "part001"},
    ).json()
    task = imported["tasks"][0]

    response = client.put(
        f"/api/tasks/{task['id']}",
        json={
            "confidential_answers": [["해당 없음"]],
            "national_tech_answers": [["해당 없음"]],
            "is_compliance": False,
        },
        headers={"X-Employee-Id": "part001"},
    )

    assert task["status"] == "UPLOADED"
    assert response.status_code == 200
    assert response.json()["status"] == "DRAFT"

    client.delete(f"/api/tasks/{task['id']}", headers={"X-Employee-Id": "part001"})


def test_admin_excel_export_supports_filters():
    client = TestClient(app)

    response = client.get(
        "/api/export/excel?status=DRAFT&is_confidential=true",
        headers={"X-Employee-Id": "admin001"},
    )

    assert response.status_code == 200
    rows = parse_workbook(response.content)
    assert rows[0][0:5] == ["실", "팀", "그룹", "파트", "소파트"]


def test_admin_excel_export_accepts_approval_status_alias():
    client = TestClient(app)

    response = client.get(
        "/api/export/excel?approval_status=DRAFT",
        headers={"X-Employee-Id": "admin001"},
    )

    assert response.status_code == 200
    rows = parse_workbook(response.content)
    assert len(rows) > 1
    assert all(row[10] == "DRAFT" for row in rows[1:])
