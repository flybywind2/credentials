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
    assert rows[0][0:3] == ["소파트", "대업무", "세부업무"]


def test_task_excel_import_creates_rows():
    client = TestClient(app)
    workbook = write_workbook(
        [
            [
                "소파트",
                "대업무",
                "세부업무",
                "기밀 문항 1",
                "기밀 데이터 유형",
                "기밀 소유자/사용자",
                "국가핵심기술 문항 1",
                "국가핵심기술 데이터 유형",
                "국가핵심기술 소유자/사용자",
                "Compliance 해당",
                "Compliance 데이터 유형",
                "Compliance 소유자/사용자",
                "보관 장소",
                "관련 메뉴",
                "공유 범위",
            ],
            [
                "엑셀",
                "엑셀 대업무",
                "엑셀 세부업무",
                "해당 없음",
                "",
                "",
                "해당 없음",
                "",
                "",
                "비해당",
                "",
                "",
                "문서함",
                "분류 메뉴",
                "실/팀/그룹",
            ],
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


def test_task_excel_import_preview_validates_without_creating_rows():
    client = TestClient(app)
    before_count = len(client.get("/api/tasks", headers={"X-Employee-Id": "part001"}).json())
    workbook = write_workbook(
        [
            [
                "소파트",
                "대업무",
                "세부업무",
                "기밀 문항 1",
                "기밀 데이터 유형",
                "기밀 소유자/사용자",
                "국가핵심기술 문항 1",
                "국가핵심기술 데이터 유형",
                "국가핵심기술 소유자/사용자",
                "Compliance 해당",
                "Compliance 데이터 유형",
                "Compliance 소유자/사용자",
                "보관 장소",
                "관련 메뉴",
                "공유 범위",
            ],
            [
                "엑셀",
                "",
                "세부업무만 있음",
                "해당 없음",
                "",
                "",
                "해당 없음",
                "",
                "",
                "비해당",
                "",
                "",
                "문서함",
                "분류 메뉴",
                "실/팀/그룹",
            ],
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
