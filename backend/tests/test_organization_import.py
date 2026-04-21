from fastapi.testclient import TestClient

from backend.main import app


CSV_TEXT = """실명,실장명,실장ID,팀명,팀장명,팀장ID,그룹명,그룹장명,그룹장ID,파트명,파트장명,파트장ID
수입실,수입실장,impd1,수입팀,수입팀장,impt1,수입그룹,수입그룹장,impg1,수입파트,수입파트장,impp1
"""


def test_admin_can_import_organizations_from_csv():
    client = TestClient(app)

    response = client.post(
        "/api/admin/organizations/import",
        files={"file": ("organizations.csv", CSV_TEXT.encode("utf-8"), "text/csv")},
        headers={"X-Employee-Id": "admin001"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["imported_count"] == 1
    assert body["organizations"][0]["part_name"] == "수입파트"
    assert body["organizations"][0]["email_preview"]["part_head_email"] == "impp1@samsung.com"


def test_inputter_cannot_import_organizations_from_csv():
    client = TestClient(app)

    response = client.post(
        "/api/admin/organizations/import",
        files={"file": ("organizations.csv", CSV_TEXT.encode("utf-8"), "text/csv")},
        headers={"X-Employee-Id": "part001"},
    )

    assert response.status_code == 403
