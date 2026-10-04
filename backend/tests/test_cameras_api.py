from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import clock
from app.config import Settings
from app.main import create_app
from app.models.camera import Camera, CameraStatus


def test_create_camera_happy_path(client: TestClient) -> None:
    """POST /api/cameras creates a new camera with status unknown and clean defaults."""
    payload = {
        "camera_name": "Front Gate",
        "location": "Main Entrance",
        "description": "Primary gate camera facing north",
        "ip_address": "192.0.2.10",
    }
    response = client.post("/api/cameras", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["id"] is not None
    assert data["camera_name"] == "Front Gate"
    assert data["location"] == "Main Entrance"
    assert data["description"] == "Primary gate camera facing north"
    assert data["ip_address"] == "192.0.2.10"
    assert data["status"] == "unknown"
    assert data["last_checked"] is None
    assert data["last_online"] is None

    # Timestamps are valid UTC datetimes
    created_at = datetime.fromisoformat(data["created_at"])
    updated_at = datetime.fromisoformat(data["updated_at"])
    assert created_at.tzinfo is not None
    assert updated_at.tzinfo is not None
    assert created_at == updated_at

    # Internal monitoring fields MUST be absent from response
    assert "consecutive_failures" not in data


def test_internal_fields_absent_from_all_endpoints(
    client: TestClient, db_session: Session
) -> None:
    """Internal fields are absent from all response models (POST, GET, PATCH, list)."""
    # 1. Create (POST)
    post_res = client.post(
        "/api/cameras",
        json={
            "camera_name": "Cam A",
            "location": "Loc A",
            "description": "Desc A",
            "ip_address": "192.0.2.20",
        },
    )
    assert post_res.status_code == 201
    post_data = post_res.json()
    camera_id = post_data["id"]
    assert "consecutive_failures" not in post_data

    # Set internal fields in DB to non-default values
    cam = db_session.get(Camera, camera_id)
    assert cam is not None
    cam.consecutive_failures = 7
    db_session.commit()

    # 2. Get Single (GET /api/cameras/{id})
    get_res = client.get(f"/api/cameras/{camera_id}")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert "consecutive_failures" not in get_data

    # 3. Patch (PATCH /api/cameras/{id})
    patch_res = client.patch(
        f"/api/cameras/{camera_id}", json={"camera_name": "Updated Cam A"}
    )
    assert patch_res.status_code == 200
    patch_data = patch_res.json()
    assert "consecutive_failures" not in patch_data

    # 4. List (GET /api/cameras)
    list_res = client.get("/api/cameras")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert len(list_data) >= 1
    for item in list_data:
        assert "consecutive_failures" not in item


def test_ip_address_whitespace_trimmed_and_canonicalized(
    client: TestClient,
) -> None:
    """Leading and trailing whitespace in ip_address is trimmed before storing."""
    payload = {
        "camera_name": "Whitespace IP Cam",
        "location": "Hallway",
        "description": "Testing IP trimming",
        "ip_address": "  192.0.2.33  ",
    }
    response = client.post("/api/cameras", json=payload)
    assert response.status_code == 201
    assert response.json()["ip_address"] == "192.0.2.33"


@pytest.mark.parametrize(
    ("bad_ip", "expected_msg", "expected_type"),
    [
        (
            "192.0.002.010",
            "Leading zeros are not permitted in IP address octets.",
            "leading_zero",
        ),
        (
            "１９２.０.２.１０",
            "Enter a valid IPv4 address such as 192.168.1.64.",
            "invalid_ipv4",
        ),
        (
            "0.0.0.0",
            "0.0.0.0 is not a valid camera host address.",
            "unspecified_address",
        ),
        (
            "224.0.0.1",
            "Multicast addresses (224.0.0.0/4) cannot be used as camera addresses.",
            "multicast_address",
        ),
        (
            "239.255.255.250",
            "Multicast addresses (224.0.0.0/4) cannot be used as camera addresses.",
            "multicast_address",
        ),
        (
            "255.255.255.255",
            (
                "255.255.255.255 is a broadcast address and cannot be used "
                "as a camera address."
            ),
            "broadcast_address",
        ),
        (
            "camera.local",
            "Enter a valid IPv4 address such as 192.168.1.64.",
            "invalid_ipv4",
        ),
        (
            "2001:db8::1",
            "Enter a valid IPv4 address such as 192.168.1.64.",
            "invalid_ipv4",
        ),
        (
            "999.999.999.999",
            "Enter a valid IPv4 address such as 192.168.1.64.",
            "invalid_ipv4",
        ),
        (
            "",
            "This field cannot be empty.",
            "empty",
        ),
    ],
)
def test_invalid_ip_addresses_rejected(
    client: TestClient, bad_ip: str, expected_msg: str, expected_type: str
) -> None:
    """Invalid IP addresses are rejected with HTTP 422 and exact error details."""
    payload = {
        "camera_name": "Test Cam",
        "location": "Test Loc",
        "description": "Test Desc",
        "ip_address": bad_ip,
    }
    response = client.post("/api/cameras", json=payload)
    assert response.status_code == 422
    errors = response.json()["detail"]
    ip_err = next(e for e in errors if "ip_address" in e["loc"])
    assert ip_err["msg"] == expected_msg
    assert ip_err["type"] == expected_type


@pytest.mark.parametrize(
    ("field", "bad_value", "expected_msg"),
    [
        (
            "camera_name",
            "Cam\nName",
            "Control characters including newlines and tabs are not allowed.",
        ),
        (
            "camera_name",
            "Cam\tName",
            "Control characters including newlines and tabs are not allowed.",
        ),
        (
            "camera_name",
            "Cam\x00Name",
            "Control characters including newlines and tabs are not allowed.",
        ),
        (
            "location",
            "Room\n101",
            "Control characters including newlines and tabs are not allowed.",
        ),
        (
            "location",
            "Room\t101",
            "Control characters including newlines and tabs are not allowed.",
        ),
        (
            "description",
            "First line\nSecond line",
            "Control characters including newlines and tabs are not allowed.",
        ),
        ("camera_name", "   ", "This field cannot be empty."),
        ("location", "   ", "This field cannot be empty."),
        ("description", "   ", "This field cannot be empty."),
        ("camera_name", "x" * 101, "Must be 100 characters or fewer."),
        ("location", "x" * 101, "Must be 100 characters or fewer."),
        ("description", "x" * 501, "Must be 500 characters or fewer."),
    ],
)
def test_text_field_validations(
    client: TestClient, field: str, bad_value: str, expected_msg: str
) -> None:
    """Text fields reject control characters, empty whitespace, and length excesses."""
    payload: dict[str, Any] = {
        "camera_name": "Valid Name",
        "location": "Valid Location",
        "description": "Valid Description",
        "ip_address": "192.0.2.50",
    }
    payload[field] = bad_value
    response = client.post("/api/cameras", json=payload)
    assert response.status_code == 422
    errors = response.json()["detail"]
    field_err = next(e for e in errors if field in e["loc"])
    assert field_err["msg"] == expected_msg


def test_extra_fields_forbidden(client: TestClient) -> None:
    """Extra fields are rejected on both POST and PATCH with HTTP 422."""
    post_payload = {
        "camera_name": "Test",
        "location": "Loc",
        "description": "Desc",
        "ip_address": "192.0.2.60",
        "extra_field": "disallowed",
    }
    post_res = client.post("/api/cameras", json=post_payload)
    assert post_res.status_code == 422

    # Create valid camera first
    valid_res = client.post(
        "/api/cameras",
        json={
            "camera_name": "Test",
            "location": "Loc",
            "description": "Desc",
            "ip_address": "192.0.2.61",
        },
    )
    camera_id = valid_res.json()["id"]

    patch_res = client.patch(
        f"/api/cameras/{camera_id}", json={"extra_field": "disallowed"}
    )
    assert patch_res.status_code == 422

    # Attempting to patch internal fields directly is also rejected as extra_forbidden
    patch_internal = client.patch(
        f"/api/cameras/{camera_id}", json={"consecutive_failures": 5}
    )
    assert patch_internal.status_code == 422


def test_duplicate_ip_handling(client: TestClient) -> None:
    """Duplicate IP returns 409 with exact error shape on POST and PATCH."""
    # Create Camera 1
    res1 = client.post(
        "/api/cameras",
        json={
            "camera_name": "Cam 1",
            "location": "Loc 1",
            "description": "Desc 1",
            "ip_address": "192.0.2.70",
        },
    )
    assert res1.status_code == 201

    # Attempt POST with same IP
    dup_post = client.post(
        "/api/cameras",
        json={
            "camera_name": "Cam 2",
            "location": "Loc 2",
            "description": "Desc 2",
            "ip_address": "192.0.2.70",
        },
    )
    assert dup_post.status_code == 409
    assert dup_post.json() == {
        "detail": [
            {
                "loc": ["body", "ip_address"],
                "msg": "A camera with this IP address already exists.",
                "type": "duplicate",
            }
        ]
    }

    # Create Camera 2 with different IP
    res2 = client.post(
        "/api/cameras",
        json={
            "camera_name": "Cam 2",
            "location": "Loc 2",
            "description": "Desc 2",
            "ip_address": "192.0.2.71",
        },
    )
    assert res2.status_code == 201
    cam2_id = res2.json()["id"]

    # Attempt PATCH Camera 2 with Camera 1's IP
    dup_patch = client.patch(
        f"/api/cameras/{cam2_id}", json={"ip_address": "192.0.2.70"}
    )
    assert dup_patch.status_code == 409
    assert dup_patch.json() == {
        "detail": [
            {
                "loc": ["body", "ip_address"],
                "msg": "A camera with this IP address already exists.",
                "type": "duplicate",
            }
        ]
    }

    # PATCH Camera 2 with its OWN existing IP -> succeeds with 200 OK
    own_patch = client.patch(
        f"/api/cameras/{cam2_id}", json={"ip_address": "192.0.2.71"}
    )
    assert own_patch.status_code == 200


def test_patch_empty_body_and_null_values_rejected(client: TestClient) -> None:
    """PATCH with empty body {} or explicit null field values returns HTTP 422."""
    create_res = client.post(
        "/api/cameras",
        json={
            "camera_name": "Test Cam",
            "location": "Test Loc",
            "description": "Test Desc",
            "ip_address": "192.0.2.80",
        },
    )
    camera_id = create_res.json()["id"]

    # Empty body
    empty_res = client.patch(f"/api/cameras/{camera_id}", json={})
    assert empty_res.status_code == 422

    # Explicit null values
    null_name = client.patch(f"/api/cameras/{camera_id}", json={"camera_name": None})
    assert null_name.status_code == 422

    null_ip = client.patch(f"/api/cameras/{camera_id}", json={"ip_address": None})
    assert null_ip.status_code == 422


def test_patch_ip_resets_monitoring_state(
    client: TestClient, db_session: Session
) -> None:
    """Changing ip_address resets monitoring state; other fields leave it untouched."""
    create_res = client.post(
        "/api/cameras",
        json={
            "camera_name": "Gate Cam",
            "location": "North Gate",
            "description": "Gate monitor",
            "ip_address": "192.0.2.90",
        },
    )
    camera_id = create_res.json()["id"]

    # Simulate active monitoring outage in DB
    now = clock.utc_now()
    cam = db_session.get(Camera, camera_id)
    assert cam is not None
    cam.status = CameraStatus.OFFLINE
    cam.last_checked = now
    cam.last_online = now
    cam.consecutive_failures = 12
    db_session.commit()

    # 1. Edit only camera_name -> monitoring state MUST remain untouched
    name_patch = client.patch(
        f"/api/cameras/{camera_id}", json={"camera_name": "Renamed Gate Cam"}
    )
    assert name_patch.status_code == 200
    db_session.expire_all()
    cam_after_name = db_session.get(Camera, camera_id)
    assert cam_after_name is not None
    assert cam_after_name.status == CameraStatus.OFFLINE
    assert cam_after_name.consecutive_failures == 12

    # 2. Edit ip_address to the SAME value -> monitoring state MUST remain untouched
    same_ip_patch = client.patch(
        f"/api/cameras/{camera_id}", json={"ip_address": "192.0.2.90"}
    )
    assert same_ip_patch.status_code == 200
    db_session.expire_all()
    cam_after_same = db_session.get(Camera, camera_id)
    assert cam_after_same is not None
    assert cam_after_same.status == CameraStatus.OFFLINE
    assert cam_after_same.consecutive_failures == 12

    # 3. Edit ip_address to a NEW value -> monitoring state MUST reset cleanly
    new_ip_patch = client.patch(
        f"/api/cameras/{camera_id}", json={"ip_address": "192.0.2.91"}
    )
    assert new_ip_patch.status_code == 200
    data = new_ip_patch.json()
    assert data["ip_address"] == "192.0.2.91"
    assert data["status"] == "unknown"
    assert data["last_checked"] is None
    assert data["last_online"] is None

    db_session.expire_all()
    cam_after_new_ip = db_session.get(Camera, camera_id)
    assert cam_after_new_ip is not None
    assert cam_after_new_ip.status == CameraStatus.UNKNOWN
    assert cam_after_new_ip.consecutive_failures == 0


def test_updated_at_advances_only_when_user_fields_change(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """created_at stays static, updated_at advances only when user fields change."""
    t1 = datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)
    t2 = datetime(2026, 1, 1, 11, 0, 0, tzinfo=UTC)
    t3 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)

    # Freeze at t1 for creation
    monkeypatch.setattr(clock, "utc_now", lambda: t1)
    create_res = client.post(
        "/api/cameras",
        json={
            "camera_name": "Warehouse",
            "location": "Aisle 3",
            "description": "Stock camera",
            "ip_address": "192.0.2.100",
        },
    )
    camera_id = create_res.json()["id"]
    data = create_res.json()
    assert datetime.fromisoformat(data["created_at"]) == t1
    assert datetime.fromisoformat(data["updated_at"]) == t1

    # Advance clock to t2, send PATCH with identical values -> updated_at unchanged
    monkeypatch.setattr(clock, "utc_now", lambda: t2)
    no_change_res = client.patch(
        f"/api/cameras/{camera_id}",
        json={"camera_name": "Warehouse", "location": "Aisle 3"},
    )
    assert no_change_res.status_code == 200
    no_change_data = no_change_res.json()
    assert datetime.fromisoformat(no_change_data["created_at"]) == t1
    assert datetime.fromisoformat(no_change_data["updated_at"]) == t1

    # Advance clock to t3, send PATCH with a new value -> updated_at MUST change to t3
    monkeypatch.setattr(clock, "utc_now", lambda: t3)
    change_res = client.patch(f"/api/cameras/{camera_id}", json={"location": "Aisle 4"})
    assert change_res.status_code == 200
    change_data = change_res.json()
    assert datetime.fromisoformat(change_data["created_at"]) == t1
    assert datetime.fromisoformat(change_data["updated_at"]) == t3


def test_camera_not_found_errors(client: TestClient) -> None:
    """GET, PATCH, and DELETE on nonexistent camera ID return 404 with exact detail."""
    get_res = client.get("/api/cameras/99999")
    assert get_res.status_code == 404
    assert get_res.json() == {"detail": "Camera not found."}

    patch_res = client.patch("/api/cameras/99999", json={"camera_name": "Ghost"})
    assert patch_res.status_code == 404
    assert patch_res.json() == {"detail": "Camera not found."}

    delete_res = client.delete("/api/cameras/99999")
    assert delete_res.status_code == 404
    assert delete_res.json() == {"detail": "Camera not found."}


def test_delete_camera_lifecycle(client: TestClient) -> None:
    """DELETE /api/cameras/{id} returns 204, then subsequent GET returns 404."""
    create_res = client.post(
        "/api/cameras",
        json={
            "camera_name": "Temporary",
            "location": "Desk",
            "description": "Testing deletion",
            "ip_address": "192.0.2.110",
        },
    )
    camera_id = create_res.json()["id"]

    delete_res = client.delete(f"/api/cameras/{camera_id}")
    assert delete_res.status_code == 204
    assert delete_res.text == ""

    # Second delete returns 404
    second_delete = client.delete(f"/api/cameras/{camera_id}")
    assert second_delete.status_code == 404

    # GET returns 404
    get_res = client.get(f"/api/cameras/{camera_id}")
    assert get_res.status_code == 404


def test_list_cameras_ordered_by_id_asc(client: TestClient) -> None:
    """GET /api/cameras returns all cameras ordered by id ascending."""
    # Initially empty
    initial_res = client.get("/api/cameras")
    assert initial_res.status_code == 200
    assert initial_res.json() == []

    # Create three cameras
    ids = []
    for i in range(1, 4):
        res = client.post(
            "/api/cameras",
            json={
                "camera_name": f"Cam {i}",
                "location": f"Loc {i}",
                "description": f"Desc {i}",
                "ip_address": f"192.0.2.12{i}",
            },
        )
        assert res.status_code == 201
        ids.append(res.json()["id"])

    list_res = client.get("/api/cameras")
    assert list_res.status_code == 200
    retrieved_ids = [c["id"] for c in list_res.json()]
    assert retrieved_ids == ids
    assert retrieved_ids == sorted(retrieved_ids)


def test_database_persistence_across_app_restart(
    test_settings: Settings, test_db_path: Path
) -> None:
    """Data persists across application restarts pointing to the same database file."""
    app1 = create_app(test_settings)
    with TestClient(app1) as client1:
        res = client1.post(
            "/api/cameras",
            json={
                "camera_name": "Persistent Cam",
                "location": "Server Room",
                "description": "Crucial persistence check",
                "ip_address": "192.0.2.150",
            },
        )
        assert res.status_code == 201
        created_id = res.json()["id"]

    # Start a brand new app and client on the same database
    app2 = create_app(test_settings)
    with TestClient(app2) as client2:
        get_res = client2.get(f"/api/cameras/{created_id}")
        assert get_res.status_code == 200
        data = get_res.json()
        assert data["camera_name"] == "Persistent Cam"
        assert data["ip_address"] == "192.0.2.150"
