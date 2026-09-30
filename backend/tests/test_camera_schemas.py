import pytest
from pydantic import ValidationError

from app.schemas.camera import CameraCreate, CameraUpdate


def test_camera_create_happy_path() -> None:
    data = {
        "camera_name": "  Front Gate  ",
        "location": "  Main Entrance  ",
        "description": "  Monitors main gate entrance  ",
        "ip_address": "  192.0.2.10  ",
    }
    camera = CameraCreate.model_validate(data)
    assert camera.camera_name == "Front Gate"
    assert camera.location == "Main Entrance"
    assert camera.description == "Monitors main gate entrance"
    assert camera.ip_address == "192.0.2.10"


@pytest.mark.parametrize(
    "allowed_ip",
    [
        "127.0.0.1",
        "10.0.0.5",
        "169.254.1.1",
        "192.168.1.64",
        "192.0.2.10",
    ],
)
def test_camera_create_allowed_ips(allowed_ip: str) -> None:
    camera = CameraCreate.model_validate(
        {
            "camera_name": "Test",
            "location": "Test",
            "description": "Test",
            "ip_address": allowed_ip,
        }
    )
    assert camera.ip_address == allowed_ip


@pytest.mark.parametrize(
    ("bad_ip", "expected_type", "expected_msg"),
    [
        ("", "empty", "This field cannot be empty."),
        ("   ", "empty", "This field cannot be empty."),
        ("abc", "invalid_ipv4", "Enter a valid IPv4 address such as 192.168.1.64."),
        (
            "192.0.2",
            "invalid_ipv4",
            "Enter a valid IPv4 address such as 192.168.1.64.",
        ),
        (
            "192.0.2.256",
            "invalid_ipv4",
            "Enter a valid IPv4 address such as 192.168.1.64.",
        ),
        (
            "192.0.2.10/24",
            "invalid_ipv4",
            "Enter a valid IPv4 address such as 192.168.1.64.",
        ),
        (
            "192.0.2.10:80",
            "invalid_ipv4",
            "Enter a valid IPv4 address such as 192.168.1.64.",
        ),
        (
            "192.0.002.010",
            "leading_zero",
            "Leading zeros are not permitted in IP address octets.",
        ),
        ("::1", "invalid_ipv4", "Enter a valid IPv4 address such as 192.168.1.64."),
        (
            "2001:db8::1",
            "invalid_ipv4",
            "Enter a valid IPv4 address such as 192.168.1.64.",
        ),
        (
            "１９２.０.２.１０",
            "invalid_ipv4",
            "Enter a valid IPv4 address such as 192.168.1.64.",
        ),
        (
            "0.0.0.0",
            "unspecified_address",
            "0.0.0.0 is not a valid camera host address.",
        ),
        (
            "224.0.0.1",
            "multicast_address",
            "Multicast addresses (224.0.0.0/4) cannot be used as camera addresses.",
        ),
        (
            "255.255.255.255",
            "broadcast_address",
            (
                "255.255.255.255 is a broadcast address and cannot be used "
                "as a camera address."
            ),
        ),
    ],
)
def test_camera_create_invalid_ips(
    bad_ip: str, expected_type: str, expected_msg: str
) -> None:
    with pytest.raises(ValidationError) as exc_info:
        CameraCreate.model_validate(
            {
                "camera_name": "Test",
                "location": "Test",
                "description": "Test",
                "ip_address": bad_ip,
            }
        )
    err = exc_info.value.errors()[0]
    assert err["loc"] == ("ip_address",)
    assert err["type"] == expected_type
    assert err["msg"] == expected_msg
    assert not err["msg"].startswith("Value error, ")


def test_camera_create_strict_string_rejects_number_and_null() -> None:
    with pytest.raises(ValidationError) as exc_info:
        CameraCreate.model_validate(
            {
                "camera_name": "Test",
                "location": "Test",
                "description": "Test",
                "ip_address": 3232235777,
            }
        )
    err = exc_info.value.errors()[0]
    assert err["loc"] == ("ip_address",)
    assert err["type"] == "string_type"


@pytest.mark.parametrize("field", ["camera_name", "location", "description"])
@pytest.mark.parametrize(
    "control_char_str",
    [
        "hello\nworld",
        "hello\tworld",
        "hello\x00world",
        "hello\rworld",
        "hello\x7fworld",
    ],
)
def test_text_fields_reject_control_characters(
    field: str, control_char_str: str
) -> None:
    data = {
        "camera_name": "Gate",
        "location": "North",
        "description": "Front entrance",
        "ip_address": "192.0.2.10",
    }
    data[field] = control_char_str
    with pytest.raises(ValidationError) as exc_info:
        CameraCreate.model_validate(data)
    err = exc_info.value.errors()[0]
    assert err["loc"] == (field,)
    assert err["type"] == "control_characters"
    assert (
        err["msg"] == "Control characters including newlines and tabs are not allowed."
    )


def test_text_field_length_limits() -> None:
    # Exactly at limit: 100 / 100 / 500 -> passes
    valid_data = {
        "camera_name": "a" * 100,
        "location": "b" * 100,
        "description": "c" * 500,
        "ip_address": "192.0.2.10",
    }
    cam = CameraCreate.model_validate(valid_data)
    assert len(cam.camera_name) == 100
    assert len(cam.location) == 100
    assert len(cam.description) == 500

    # Over limit: 101 -> fails
    with pytest.raises(ValidationError) as exc_info:
        CameraCreate.model_validate({**valid_data, "camera_name": "a" * 101})
    err = exc_info.value.errors()[0]
    assert err["loc"] == ("camera_name",)
    assert err["type"] == "too_long"
    assert err["msg"] == "Must be 100 characters or fewer."

    with pytest.raises(ValidationError) as exc_info:
        CameraCreate.model_validate({**valid_data, "description": "c" * 501})
    err_desc = exc_info.value.errors()[0]
    assert err_desc["loc"] == ("description",)
    assert err_desc["type"] == "too_long"
    assert err_desc["msg"] == "Must be 500 characters or fewer."


def test_extra_fields_forbidden() -> None:
    with pytest.raises(ValidationError) as exc_info:
        CameraCreate.model_validate(
            {
                "camera_name": "Cam",
                "location": "Loc",
                "description": "Desc",
                "ip_address": "192.0.2.10",
                "status": "online",
            }
        )
    err = exc_info.value.errors()[0]
    assert err["type"] == "extra_forbidden"


def test_camera_update_empty_body_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
        CameraUpdate.model_validate({})
    err = exc_info.value.errors()[0]
    assert err["type"] == "empty_body"
    assert err["msg"] == "At least one field must be provided for update."


def test_camera_update_explicit_null_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
        CameraUpdate.model_validate({"camera_name": None})
    err = exc_info.value.errors()[0]
    assert err["loc"] == ("camera_name",)
    assert err["type"] == "null_value"
    assert err["msg"] == "Field cannot be null."


def test_camera_update_partial_update_succeeds() -> None:
    up = CameraUpdate.model_validate({"camera_name": "New Name"})
    assert up.camera_name == "New Name"
    assert "camera_name" in up.model_fields_set
    assert "location" not in up.model_fields_set
    assert up.location is None
