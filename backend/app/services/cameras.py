from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import clock
from app.exceptions import CameraNotFoundError, DuplicateIpError
from app.models.camera import Camera, CameraStatus
from app.schemas.camera import CameraCreate, CameraUpdate


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
        alert_sent_for_current_outage=False,
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
        camera.alert_sent_for_current_outage = False

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
