from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_get_settings_returns_env_default_when_nothing_saved(
    client: TestClient,
) -> None:
    """GET /api/settings returns environment default when no interval is saved."""
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert data == {"check_interval_seconds": 60}


def test_patch_settings_persists_across_app_rebuild(test_db_path: Path) -> None:
    """PATCH /api/settings persists value across recreating app on same DB file."""
    settings_a = Settings(
        database_url=f"sqlite:///{test_db_path.as_posix()}",
        monitor_interval_seconds=60,
    )
    app_a = create_app(settings_a)

    with TestClient(app_a) as client_a:
        # Patch to 120 seconds
        patch_res = client_a.patch(
            "/api/settings",
            json={"check_interval_seconds": 120},
        )
        assert patch_res.status_code == 200
        assert patch_res.json() == {"check_interval_seconds": 120}

        get_res = client_a.get("/api/settings")
        assert get_res.json() == {"check_interval_seconds": 120}

    # Rebuild app on same DB file
    settings_b = Settings(
        database_url=f"sqlite:///{test_db_path.as_posix()}",
        monitor_interval_seconds=60,
    )
    app_b = create_app(settings_b)
    with TestClient(app_b) as client_b:
        get_res_b = client_b.get("/api/settings")
        assert get_res_b.status_code == 200
        assert get_res_b.json() == {"check_interval_seconds": 120}


@pytest.mark.parametrize(
    ("invalid_val", "expected_msg"),
    [
        (9, "Choose an interval between 10 seconds and 365 days."),
        (31536001, "Choose an interval between 10 seconds and 365 days."),
        (0, "Choose an interval between 10 seconds and 365 days."),
        (-1, "Choose an interval between 10 seconds and 365 days."),
    ],
)
def test_patch_settings_bounds_validation(
    client: TestClient,
    invalid_val: int,
    expected_msg: str,
) -> None:
    """Out-of-bound intervals produce 422 with the exact custom error message."""
    response = client.patch(
        "/api/settings",
        json={"check_interval_seconds": invalid_val},
    )
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any(
        err.get("loc") == ["body", "check_interval_seconds"]
        and err.get("msg") == expected_msg
        for err in data["detail"]
    )


@pytest.mark.parametrize(
    "invalid_payload",
    [
        {"check_interval_seconds": 10.5},
        {"check_interval_seconds": "60"},
        {"check_interval_seconds": True},
        {"check_interval_seconds": None},
        {},
        {"check_interval_seconds": 60, "extra_field": "disallowed"},
    ],
)
def test_patch_settings_type_and_extra_validation(
    client: TestClient,
    invalid_payload: dict[str, object],
) -> None:
    """Non-strict-int, null, empty dict, or extra fields are rejected with 422."""
    response = client.patch("/api/settings", json=invalid_payload)
    assert response.status_code == 422


def test_patch_settings_empty_body_422(client: TestClient) -> None:
    """Empty HTTP body returns 422."""
    response = client.patch(
        "/api/settings",
        content=b"",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


def test_patch_settings_accepted_bounds(client: TestClient) -> None:
    """Minimum (10) and maximum (31536000) interval bounds are accepted."""
    res_min = client.patch(
        "/api/settings",
        json={"check_interval_seconds": 10},
    )
    assert res_min.status_code == 200
    assert res_min.json() == {"check_interval_seconds": 10}

    res_max = client.patch(
        "/api/settings",
        json={"check_interval_seconds": 31536000},
    )
    assert res_max.status_code == 200
    assert res_max.json() == {"check_interval_seconds": 31536000}


def test_saving_does_not_start_stopped_engine_or_mutate_cameras(
    client: TestClient,
    test_db_path: Path,
) -> None:
    """Saving settings never starts engine, nor mutates cameras or running flag."""
    # Add a camera
    add_res = client.post(
        "/api/cameras",
        json={
            "camera_name": "Test Cam",
            "location": "Lobby",
            "description": "Desk view",
            "ip_address": "192.0.2.55",
        },
    )
    assert add_res.status_code == 201

    # Ensure engine is stopped
    status_res = client.get("/api/monitoring/status")
    assert status_res.json()["running"] is False

    # Patch settings
    patch_res = client.patch(
        "/api/settings",
        json={"check_interval_seconds": 30},
    )
    assert patch_res.status_code == 200

    # Verify status still stopped, but reflects new interval
    status_after = client.get("/api/monitoring/status").json()
    assert status_after["running"] is False
    assert status_after["interval_seconds"] == 30
    assert status_after["total"] == 1

    # Verify camera in DB is unchanged
    cam_res = client.get("/api/cameras")
    assert len(cam_res.json()) == 1
    assert cam_res.json()[0]["ip_address"] == "192.0.2.55"
