import ipaddress
from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, StrictStr, field_validator, model_validator
from pydantic_core import PydanticCustomError

from app.models.camera import CameraStatus


def validate_text_field(value: str, max_length: int) -> str:
    """Trim whitespace, reject empty strings, control characters, and overflow."""
    trimmed = value.strip()
    if not trimmed:
        raise PydanticCustomError("empty", "This field cannot be empty.")

    for char in trimmed:
        code = ord(char)
        if code < 32 or code == 127:
            raise PydanticCustomError(
                "control_characters",
                "Control characters including newlines and tabs are not allowed.",
            )

    if len(trimmed) > max_length:
        raise PydanticCustomError(
            "too_long",
            f"Must be {max_length} characters or fewer.",
        )

    return trimmed


def validate_ip_address(value: str) -> str:
    """Validate and canonicalize an IPv4 address.

    Trims whitespace and stores the canonical string representation.
    Rejects 0.0.0.0, multicast (224.0.0.0/4), broadcast (255.255.255.255),
    and leading zeros (e.g. 192.0.002.010).
    Allows loopback, link-local, and private ranges.
    """
    trimmed = value.strip()
    if not trimmed:
        raise PydanticCustomError("empty", "This field cannot be empty.")

    # Check for leading zero octets (e.g., '192.0.002.010')
    parts = trimmed.split(".")
    if len(parts) == 4:
        for part in parts:
            if len(part) > 1 and part.startswith("0"):
                raise PydanticCustomError(
                    "leading_zero",
                    "Leading zeros are not permitted in IP address octets.",
                )

    try:
        ip = ipaddress.IPv4Address(trimmed)
    except (ipaddress.AddressValueError, ValueError):
        raise PydanticCustomError(
            "invalid_ipv4",
            "Enter a valid IPv4 address such as 192.168.1.64.",
        ) from None

    if ip == ipaddress.IPv4Address("0.0.0.0"):
        raise PydanticCustomError(
            "unspecified_address",
            "0.0.0.0 is not a valid camera host address.",
        )

    if ip.is_multicast:
        raise PydanticCustomError(
            "multicast_address",
            "Multicast addresses (224.0.0.0/4) cannot be used as camera addresses.",
        )

    if ip == ipaddress.IPv4Address("255.255.255.255"):
        raise PydanticCustomError(
            "broadcast_address",
            (
                "255.255.255.255 is a broadcast address and cannot be used "
                "as a camera address."
            ),
        )

    return str(ip)


class CameraCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    camera_name: StrictStr
    location: StrictStr
    description: StrictStr
    ip_address: StrictStr

    @field_validator("camera_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return validate_text_field(v, max_length=100)

    @field_validator("location")
    @classmethod
    def validate_loc(cls, v: str) -> str:
        return validate_text_field(v, max_length=100)

    @field_validator("description")
    @classmethod
    def validate_desc(cls, v: str) -> str:
        return validate_text_field(v, max_length=500)

    @field_validator("ip_address")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        return validate_ip_address(v)


class CameraUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    camera_name: StrictStr | None = None
    location: StrictStr | None = None
    description: StrictStr | None = None
    ip_address: StrictStr | None = None

    @field_validator("camera_name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        if v is None:
            raise PydanticCustomError("null_value", "Field cannot be null.")
        return validate_text_field(v, max_length=100)

    @field_validator("location")
    @classmethod
    def validate_loc(cls, v: str | None) -> str | None:
        if v is None:
            raise PydanticCustomError("null_value", "Field cannot be null.")
        return validate_text_field(v, max_length=100)

    @field_validator("description")
    @classmethod
    def validate_desc(cls, v: str | None) -> str | None:
        if v is None:
            raise PydanticCustomError("null_value", "Field cannot be null.")
        return validate_text_field(v, max_length=500)

    @field_validator("ip_address")
    @classmethod
    def validate_ip(cls, v: str | None) -> str | None:
        if v is None:
            raise PydanticCustomError("null_value", "Field cannot be null.")
        return validate_ip_address(v)

    @model_validator(mode="after")
    def validate_not_empty_body(self) -> Self:
        if not self.model_fields_set:
            raise PydanticCustomError(
                "empty_body",
                "At least one field must be provided for update.",
            )
        return self


class CameraRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    camera_name: str
    location: str
    description: str
    ip_address: str
    status: CameraStatus | str
    last_checked: datetime | None
    last_online: datetime | None
    created_at: datetime
    updated_at: datetime


CAMERA_CSV_HEADERS: list[str] = [
    "camera_name",
    "location",
    "description",
    "ip_address",
]

CAMERA_EXPORT_HEADERS: list[str] = [
    *CAMERA_CSV_HEADERS,
    "status",
    "last_checked",
    "last_online",
]


class CameraImportPreview(BaseModel):
    count: int
    preview: list[CameraCreate]


class CameraImportSuccess(BaseModel):
    imported: int


class CameraImportErrorItem(BaseModel):
    loc: list[str | int]
    msg: str
    type: str


class CameraImportErrorResponse(BaseModel):
    detail: list[CameraImportErrorItem]
    total_errors: int
