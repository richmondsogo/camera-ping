import mimetypes
from pathlib import Path
import pytest
from fastapi import FastAPI, Response
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.models.camera import Camera
from app.models.monitoring import MonitoringState
from tests.conftest import make_test_client


def test_production_mode_disables_docs(tmp_path: Path) -> None:
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text("<html>App</html>", encoding="utf-8")

    db_path = tmp_path / "prod.db"
    settings = Settings(
        database_url=f"sqlite:///{db_path.as_posix()}",
        frontend_dist=dist_dir,
    )
    app = create_app(settings)

    with make_test_client(app) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/redoc").status_code == 404
        assert client.get("/openapi.json").status_code == 404


def test_dev_mode_keeps_docs(tmp_path: Path) -> None:
    db_path = tmp_path / "dev.db"
    settings = Settings(
        database_url=f"sqlite:///{db_path.as_posix()}",
        frontend_dist=None,
    )
    app = create_app(settings)

    with make_test_client(app) as client:
        assert client.get("/docs").status_code == 200
        assert client.get("/openapi.json").status_code == 200


def test_frontend_serving_spa_and_assets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    assets_dir = dist_dir / "assets"
    assets_dir.mkdir()

    (dist_dir / "index.html").write_text("<!doctype html><html>Root Index</html>", encoding="utf-8")
    (dist_dir / "favicon.ico").write_bytes(b"\x00\x00\x01\x00")
    (assets_dir / "app.js").write_text("console.log('hi');", encoding="utf-8")
    (assets_dir / "style.css").write_text("body { margin: 0; }", encoding="utf-8")

    # Secret file next to dist directory
    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("TOP_SECRET_DATA", encoding="utf-8")

    # Patch mimetypes so .js would be text/plain if mimetypes was used
    monkeypatch.setattr(mimetypes, "types_map", {".js": "text/plain"})

    db_path = tmp_path / "prod.db"
    settings = Settings(
        database_url=f"sqlite:///{db_path.as_posix()}",
        frontend_dist=dist_dir,
    )
    app = create_app(settings)

    with make_test_client(app) as client:
        # Root / returns index.html
        res_root = client.get("/")
        assert res_root.status_code == 200
        assert "Root Index" in res_root.text
        assert res_root.headers["content-type"].startswith("text/html")
        assert res_root.headers["cache-control"] == "no-cache"
        assert res_root.headers["x-content-type-options"] == "nosniff"
        assert res_root.headers["x-frame-options"] == "DENY"
        assert res_root.headers["referrer-policy"] == "no-referrer"

        # Client-side routes return index.html
        res_settings = client.get("/settings")
        assert res_settings.status_code == 200
        assert "Root Index" in res_settings.text

        res_unknown_route = client.get("/nonexistent-client-route")
        assert res_unknown_route.status_code == 200
        assert "Root Index" in res_unknown_route.text

        # /assets/app.js served with text/javascript regardless of mimetypes patch
        res_js = client.get("/assets/app.js")
        assert res_js.status_code == 200
        assert res_js.headers["content-type"].startswith("text/javascript")
        assert res_js.headers["cache-control"] == "public, max-age=31536000, immutable"

        # Missing asset with extension returns 404, never index.html
        res_missing_js = client.get("/assets/missing.js")
        assert res_missing_js.status_code == 404
        assert "Root Index" not in res_missing_js.text

        # Unknown /api/... returns JSON 404, never index.html
        res_api = client.get("/api/nope")
        assert res_api.status_code == 404
        assert res_api.headers["content-type"].startswith("application/json")
        assert "Root Index" not in res_api.text

        # Path traversal attack tests
        traversal_paths = [
            "/../secret.txt",
            "/%2e%2e/secret.txt",
            "/..%2fsecret.txt",
            "/%2e%2e%2fsecret.txt",
            "/..%5csecret.txt",
            "/assets/../../secret.txt",
            "/%252e%252e/secret.txt",
        ]
        for trav in traversal_paths:
            res_trav = client.get(trav)
            assert res_trav.status_code in (400, 404)
            assert "TOP_SECRET_DATA" not in res_trav.text


def test_host_header_validation(tmp_path: Path) -> None:
    db_path = tmp_path / "host.db"
    settings = Settings(database_url=f"sqlite:///{db_path.as_posix()}")
    app = create_app(settings)

    with make_test_client(app) as client:
        # Accepted Host headers
        assert client.get("/api/health", headers={"host": "localhost"}).status_code == 200
        assert client.get("/api/health", headers={"host": "localhost:8000"}).status_code == 200
        assert client.get("/api/health", headers={"host": "127.0.0.1"}).status_code == 200
        assert client.get("/api/health", headers={"host": "127.0.0.1:8742"}).status_code == 200
        assert client.get("/api/health", headers={"host": "LOCALHOST:8742"}).status_code == 200

        # Rejected Host headers (Amendment 10)
        assert client.get("/api/health", headers={"host": "localhost.evil.com"}).status_code == 400
        assert client.get("/api/health", headers={"host": "127.0.0.1.evil.com"}).status_code == 400
        assert client.get("/api/health", headers={"host": "evil.com"}).status_code == 400
        assert client.get("/api/health", headers={"host": ""}).status_code == 400


def test_origin_header_validation_and_no_state_change(tmp_path: Path) -> None:
    db_path = tmp_path / "origin.db"
    settings = Settings(database_url=f"sqlite:///{db_path.as_posix()}")
    app = create_app(settings, pinger=lambda ip: True)

    with make_test_client(app) as client:
        # Start monitoring first with clean request
        start_res = client.post("/api/monitoring/start")
        assert start_res.status_code == 200
        assert start_res.json()["running"] is True

        # Mutating requests with evil origins must be 403 AND produce NO state change
        evil_origins = [
            "http://localhost.evil.com",
            "http://127.0.0.1@evil.com",
            "null",
            "https://evil.com",
        ]

        for evil in evil_origins:
            # Attempt to stop monitoring
            res = client.post("/api/monitoring/stop", headers={"origin": evil})
            assert res.status_code == 403
            assert res.json() == {"detail": "Cross-site request refused."}

            # Verify monitoring state was NOT changed (still running)
            status_res = client.get("/api/monitoring/status")
            assert status_res.json()["running"] is True

        # Allowed Origin with different port passes
        allowed_res = client.post(
            "/api/monitoring/stop",
            headers={"origin": "http://localhost:5173"},
        )
        assert allowed_res.status_code == 200
        assert allowed_res.json()["running"] is False

        # No Origin header passes (e.g. curl / internal)
        start_again = client.post("/api/monitoring/start")
        assert start_again.status_code == 200
        assert start_again.json()["running"] is True

        # GET request with foreign origin is allowed
        get_res = client.get("/api/monitoring/status", headers={"origin": "https://evil.com"})
        assert get_res.status_code == 200


def test_security_headers_on_all_responses(tmp_path: Path) -> None:
    """Amendment 1: Security headers must be present on 200, 400, 403, 404, and injected 500."""
    db_path = tmp_path / "headers.db"
    settings = Settings(database_url=f"sqlite:///{db_path.as_posix()}")
    app = create_app(settings)

    # Add a route that raises an unhandled exception for testing 500
    @app.get("/api/crash")
    def crash():
        raise RuntimeError("Injected 500 crash")

    with make_test_client(app, raise_server_exceptions=False) as client:
        # 200
        res200 = client.get("/api/health")
        assert res200.status_code == 200
        assert res200.headers["x-content-type-options"] == "nosniff"
        assert res200.headers["x-frame-options"] == "DENY"
        assert res200.headers["referrer-policy"] == "no-referrer"

        # 400 (Bad Host)
        res400 = client.get("/api/health", headers={"host": "evil.com"})
        assert res400.status_code == 400
        assert res400.headers["x-content-type-options"] == "nosniff"
        assert res400.headers["x-frame-options"] == "DENY"
        assert res400.headers["referrer-policy"] == "no-referrer"

        # 403 (Cross-site Origin)
        res403 = client.post("/api/monitoring/stop", headers={"origin": "https://evil.com"})
        assert res403.status_code == 403
        assert res403.headers["x-content-type-options"] == "nosniff"
        assert res403.headers["x-frame-options"] == "DENY"
        assert res403.headers["referrer-policy"] == "no-referrer"

        # 404 (Unknown route)
        res404 = client.get("/api/unknown_route")
        assert res404.status_code == 404
        assert res404.headers["x-content-type-options"] == "nosniff"
        assert res404.headers["x-frame-options"] == "DENY"
        assert res404.headers["referrer-policy"] == "no-referrer"

        # 500 (Unhandled exception)
        res500 = client.get("/api/crash")
        assert res500.status_code == 500
        assert res500.headers["x-content-type-options"] == "nosniff"
        assert res500.headers["x-frame-options"] == "DENY"
        assert res500.headers["referrer-policy"] == "no-referrer"
