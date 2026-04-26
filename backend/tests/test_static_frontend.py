from fastapi.testclient import TestClient

from backend.main import app


def test_root_serves_frontend_html():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "기밀분류시스템" in response.text
    assert "/assets/favicon.svg" in response.text


def test_frontend_cache_keys_include_latest_visual_modules():
    client = TestClient(app)
    response = client.get("/")

    assert "/css/style.css?v=20260426-visual-refresh" in response.text
    assert "/js/app.js?v=20260426-paste-only-import" in response.text


def test_known_spa_paths_serve_frontend_html():
    client = TestClient(app)

    for path in [
        "/inputter",
        "/status",
        "/group",
        "/approver",
        "/approver/approvals/123",
        "/admin",
    ]:
        response = client.get(path)
        assert response.status_code == 200
        assert "기밀분류시스템" in response.text


def test_favicon_asset_is_served():
    client = TestClient(app)
    response = client.get("/assets/favicon.svg")
    assert response.status_code == 200
    assert "image/svg+xml" in response.headers["content-type"]
