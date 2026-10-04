import csv
import io
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import clock
from app.exceptions import CameraNotFoundError, DuplicateIpError, ImportConflictError
from app.models.camera import Camera, CameraStatus
from app.schemas.camera import (
    CAMERA_CSV_HEADERS,
    CAMERA_EXPORT_HEADERS,
    CameraCreate,
    CameraUpdate,
    validate_ip_address,
)


@dataclass
class ImportValidationResult:
    errors: list[dict[str, Any]]
    total_errors: int
    valid_cameras: list[CameraCreate]


def list_cameras(db: Session) -> Sequence[Camera]:
    """Return all cameras ordered by id ascending."""
    stmt = select(Camera).order_by(Camera.id.asc())
    return db.scalars(stmt).all()


def get_camera(db: Session, camera_id: int) -> Camera:
    """Retrieve a camera by id, or raise CameraNotFoundError."""
    camera = db.get(Camera, camera_id)
    if camera is None:
        raise CameraNotFoundError()
    return camera


def create_camera(db: Session, camera_in: CameraCreate) -> Camera:
    """Create a new camera record with clean initial monitoring state."""
    now = clock.utc_now()
    camera = Camera(
        camera_name=camera_in.camera_name,
        location=camera_in.location,
        description=camera_in.description,
        ip_address=camera_in.ip_address,
        status=CameraStatus.UNKNOWN,
        last_checked=None,
        last_online=None,
        consecutive_failures=0,
        created_at=now,
        updated_at=now,
    )
    db.add(camera)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateIpError() from exc
    db.refresh(camera)
    return camera


def update_camera(db: Session, camera_id: int, camera_update: CameraUpdate) -> Camera:
    """Update user-managed camera fields.

    If ip_address is changed, resets monitoring state in the same transaction.
    updated_at changes ONLY when a user-managed field actually changes value.
    """
    camera = get_camera(db, camera_id)

    has_changes = False
    ip_changed = False

    if "camera_name" in camera_update.model_fields_set:
        if (
            camera_update.camera_name is not None
            and camera_update.camera_name != camera.camera_name
        ):
            camera.camera_name = camera_update.camera_name
            has_changes = True

    if "location" in camera_update.model_fields_set:
        if (
            camera_update.location is not None
            and camera_update.location != camera.location
        ):
            camera.location = camera_update.location
            has_changes = True

    if "description" in camera_update.model_fields_set:
        if (
            camera_update.description is not None
            and camera_update.description != camera.description
        ):
            camera.description = camera_update.description
            has_changes = True

    if "ip_address" in camera_update.model_fields_set:
        if (
            camera_update.ip_address is not None
            and camera_update.ip_address != camera.ip_address
        ):
            camera.ip_address = camera_update.ip_address
            has_changes = True
            ip_changed = True

    if ip_changed:
        camera.status = CameraStatus.UNKNOWN
        camera.last_checked = None
        camera.last_online = None
        camera.consecutive_failures = 0

    if has_changes:
        camera.updated_at = clock.utc_now()

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateIpError() from exc

    db.refresh(camera)
    return camera


def delete_camera(db: Session, camera_id: int) -> None:
    """Delete a camera record or raise CameraNotFoundError."""
    camera = get_camera(db, camera_id)
    db.delete(camera)
    db.commit()


def generate_csv_template() -> str:
    """Generate the camera import CSV template containing only the header line."""
    return ",".join(CAMERA_CSV_HEADERS) + "\r\n"


def export_cameras_csv(db: Session) -> str:
    """Export all cameras in order of ID ascending as CSV with UTF-8 BOM and CRLF."""
    cameras = list_cameras(db)
    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerow(CAMERA_EXPORT_HEADERS)
    for cam in cameras:
        writer.writerow(
            [
                cam.camera_name,
                cam.location,
                cam.description,
                cam.ip_address,
                str(cam.status),
                cam.last_checked.isoformat() if cam.last_checked else "",
                cam.last_online.isoformat() if cam.last_online else "",
            ]
        )
    return output.getvalue()


def parse_and_validate_camera_csv(db: Session, csv_text: str) -> ImportValidationResult:
    """Parse and validate camera CSV content.

    Enforces UTF-8, no NUL bytes, strict header equality, 1-1000 row limits,
    per-row CameraCreate validation, canonical IP duplicate checks (in-file
    and against DB), and line tracking based on csv.reader.line_num.
    """
    if "\0" in csv_text:
        return ImportValidationResult(
            errors=[
                {
                    "loc": ["file"],
                    "msg": "The file contains NUL bytes.",
                    "type": "file_error",
                }
            ],
            total_errors=1,
            valid_cameras=[],
        )

    if not csv_text.strip():
        return ImportValidationResult(
            errors=[
                {
                    "loc": ["file"],
                    "msg": "The file has no cameras.",
                    "type": "empty_file",
                }
            ],
            total_errors=1,
            valid_cameras=[],
        )

    reader = csv.reader(io.StringIO(csv_text), strict=True)

    try:
        header_row = next(reader)
    except StopIteration:
        return ImportValidationResult(
            errors=[
                {
                    "loc": ["file"],
                    "msg": "The file has no cameras.",
                    "type": "empty_file",
                }
            ],
            total_errors=1,
            valid_cameras=[],
        )
    except csv.Error as exc:
        return ImportValidationResult(
            errors=[
                {
                    "loc": ["file"],
                    "msg": f"CSV parse error: {exc}",
                    "type": "parse_error",
                }
            ],
            total_errors=1,
            valid_cameras=[],
        )

    trimmed_header = [col.strip() for col in header_row]
    if trimmed_header != CAMERA_CSV_HEADERS:
        first_line = csv_text.splitlines()[0] if csv_text.splitlines() else ""
        semicolon_hint = ""
        if ";" in first_line and "," not in first_line:
            semicolon_hint = (
                " This looks semicolon-separated. "
                "Save the file with commas as separators."
            )
        expected_str = ",".join(CAMERA_CSV_HEADERS)
        found_str = ",".join(trimmed_header) if trimmed_header else "(empty)"
        return ImportValidationResult(
            errors=[
                {
                    "loc": ["file"],
                    "msg": (
                        f"Invalid CSV header. Expected: {expected_str}. "
                        f"Found: {found_str}.{semicolon_hint}"
                    ),
                    "type": "invalid_header",
                }
            ],
            total_errors=1,
            valid_cameras=[],
        )

    data_rows: list[tuple[int, list[str]]] = []
    while True:
        start_line = reader.line_num + 1
        try:
            row = next(reader)
        except StopIteration:
            break
        except csv.Error as exc:
            return ImportValidationResult(
                errors=[
                    {
                        "loc": ["file", start_line],
                        "msg": f"CSV parse error: {exc}",
                        "type": "parse_error",
                    }
                ],
                total_errors=1,
                valid_cameras=[],
            )

        # Skip completely blank lines
        if not row or (len(row) == 1 and not row[0].strip()):
            continue

        data_rows.append((start_line, row))

    if not data_rows:
        return ImportValidationResult(
            errors=[
                {
                    "loc": ["file"],
                    "msg": "The file has no cameras.",
                    "type": "empty_file",
                }
            ],
            total_errors=1,
            valid_cameras=[],
        )

    if len(data_rows) > 1000:
        return ImportValidationResult(
            errors=[
                {
                    "loc": ["file"],
                    "msg": (
                        f"The file has {len(data_rows)} cameras, "
                        "which exceeds the limit of 1000."
                    ),
                    "type": "too_many_rows",
                }
            ],
            total_errors=1,
            valid_cameras=[],
        )

    existing_ips = set(db.scalars(select(Camera.ip_address)).all())
    seen_ips_in_file: dict[str, int] = {}
    all_errors: list[dict[str, Any]] = []
    valid_cameras: list[CameraCreate] = []

    for start_line, row in data_rows:
        if len(row) != 4:
            all_errors.append(
                {
                    "loc": ["file", start_line, "row"],
                    "msg": f"Expected 4 fields, found {len(row)}.",
                    "type": "field_count",
                }
            )
            continue

        row_dict = {
            "camera_name": row[0],
            "location": row[1],
            "description": row[2],
            "ip_address": row[3],
        }
        has_row_error = False
        validated_camera: CameraCreate | None = None
        try:
            validated_camera = CameraCreate.model_validate(row_dict)
        except ValidationError as exc:
            has_row_error = True
            for err in exc.errors():
                col = str(err["loc"][0]) if err["loc"] else "row"
                all_errors.append(
                    {
                        "loc": ["file", start_line, col],
                        "msg": err["msg"],
                        "type": err["type"],
                    }
                )

        canonical_ip: str | None = None
        if validated_camera is not None:
            canonical_ip = validated_camera.ip_address
        else:
            try:
                canonical_ip = validate_ip_address(row[3])
            except Exception:
                canonical_ip = None

        if canonical_ip is not None:
            if canonical_ip in seen_ips_in_file:
                earlier_line = seen_ips_in_file[canonical_ip]
                all_errors.append(
                    {
                        "loc": ["file", start_line, "ip_address"],
                        "msg": f"Same IP address as row {earlier_line}.",
                        "type": "duplicate",
                    }
                )
                has_row_error = True
            else:
                seen_ips_in_file[canonical_ip] = start_line
                if canonical_ip in existing_ips:
                    all_errors.append(
                        {
                            "loc": ["file", start_line, "ip_address"],
                            "msg": "A camera with this IP address already exists.",
                            "type": "duplicate",
                        }
                    )
                    has_row_error = True

        if not has_row_error and validated_camera is not None:
            valid_cameras.append(validated_camera)

    def error_sort_key(err: dict[str, Any]) -> tuple[int, str]:
        loc = err.get("loc", [])
        if len(loc) >= 2 and isinstance(loc[1], int):
            col = str(loc[2]) if len(loc) > 2 else ""
            return (loc[1], col)
        return (0, "")

    all_errors.sort(key=error_sort_key)
    return ImportValidationResult(
        errors=all_errors,
        total_errors=len(all_errors),
        valid_cameras=valid_cameras,
    )


def commit_imported_cameras(db: Session, cameras_in: list[CameraCreate]) -> int:
    """Insert validated cameras in a single transaction with defaults."""
    now = clock.utc_now()
    for camera_in in cameras_in:
        camera = Camera(
            camera_name=camera_in.camera_name,
            location=camera_in.location,
            description=camera_in.description,
            ip_address=camera_in.ip_address,
            status=CameraStatus.UNKNOWN,
            last_checked=None,
            last_online=None,
            consecutive_failures=0,
            created_at=now,
            updated_at=now,
        )
        db.add(camera)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ImportConflictError() from exc
    return len(cameras_in)
