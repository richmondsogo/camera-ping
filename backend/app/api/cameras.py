from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app import clock
from app.database import get_db
from app.exceptions import ImportConflictError
from app.models.camera import Camera
from app.schemas.camera import CameraCreate, CameraRead, CameraUpdate
from app.services import cameras as cameras_service

router = APIRouter(prefix="/api/cameras", tags=["cameras"])

DbSession = Annotated[Session, Depends(get_db)]

MAX_IMPORT_BYTES = 1024 * 1024  # 1 MiB


@router.get("", response_model=list[CameraRead], status_code=status.HTTP_200_OK)
def list_cameras(db: DbSession) -> Sequence[Camera]:
    """Retrieve all cameras ordered by id ascending."""
    return cameras_service.list_cameras(db)


@router.post("", response_model=CameraRead, status_code=status.HTTP_201_CREATED)
def create_camera(camera_in: CameraCreate, db: DbSession) -> Camera:
    """Create a new camera record."""
    return cameras_service.create_camera(db, camera_in)


@router.get(
    "/import/template",
    response_class=Response,
    status_code=status.HTTP_200_OK,
)
def get_import_template() -> Response:
    """Return CSV template containing only the header line."""
    content = cameras_service.generate_csv_template()
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=camera-template.csv"},
    )


@router.get(
    "/export",
    response_class=Response,
    status_code=status.HTTP_200_OK,
)
def export_cameras(db: DbSession) -> Response:
    """Export all cameras ordered by id ascending as CSV with UTF-8 BOM and CRLF."""
    today_str = clock.utc_now().strftime("%Y-%m-%d")
    filename = f"cameras-{today_str}.csv"
    csv_content = cameras_service.export_cameras_csv(db)
    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post(
    "/import",
    status_code=status.HTTP_200_OK,
)
async def import_cameras(
    request: Request,
    db: DbSession,
    dry_run: bool = Query(default=False),
) -> Response:
    """Import cameras from CSV with dry-run validation and atomic insertion."""
    body_bytes = bytearray()
    async for chunk in request.stream():
        body_bytes.extend(chunk)
        if len(body_bytes) > MAX_IMPORT_BYTES:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={
                    "detail": [
                        {
                            "loc": ["file"],
                            "msg": "File size exceeds maximum limit of 1 MiB.",
                            "type": "file_too_large",
                        }
                    ],
                    "total_errors": 1,
                },
            )

    try:
        csv_text = bytes(body_bytes).decode("utf-8-sig")
    except UnicodeDecodeError:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": [
                    {
                        "loc": ["file"],
                        "msg": (
                            "The file isn't UTF-8. "
                            "In Excel, use Save As and choose CSV UTF-8."
                        ),
                        "type": "encoding_error",
                    }
                ],
                "total_errors": 1,
            },
        )

    validation = cameras_service.parse_and_validate_camera_csv(db, csv_text)
    if validation.errors:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": validation.errors[:100],
                "total_errors": validation.total_errors,
            },
        )

    if dry_run:
        preview_rows = [c.model_dump() for c in validation.valid_cameras[:5]]
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "count": len(validation.valid_cameras),
                "preview": preview_rows,
            },
        )

    try:
        imported_count = cameras_service.commit_imported_cameras(
            db, validation.valid_cameras
        )
    except ImportConflictError:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "detail": [
                    {
                        "loc": ["file"],
                        "msg": (
                            "Another camera with one of these IP addresses "
                            "was added in the meantime. "
                            "Nothing was imported. Try again."
                        ),
                        "type": "duplicate",
                    }
                ]
            },
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"imported": imported_count},
    )


@router.get("/{camera_id}", response_model=CameraRead, status_code=status.HTTP_200_OK)
def get_camera(camera_id: int, db: DbSession) -> Camera:
    """Retrieve a single camera by id."""
    return cameras_service.get_camera(db, camera_id)


@router.patch("/{camera_id}", response_model=CameraRead, status_code=status.HTTP_200_OK)
def update_camera(camera_id: int, camera_update: CameraUpdate, db: DbSession) -> Camera:
    """Update camera user-managed fields."""
    return cameras_service.update_camera(db, camera_id, camera_update)


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_camera(camera_id: int, db: DbSession) -> Response:
    """Delete a camera by id."""
    cameras_service.delete_camera(db, camera_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
