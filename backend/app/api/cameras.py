from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.camera import Camera
from app.schemas.camera import CameraCreate, CameraRead, CameraUpdate
from app.services import cameras as cameras_service

router = APIRouter(prefix="/api/cameras", tags=["cameras"])

DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[CameraRead], status_code=status.HTTP_200_OK)
def list_cameras(db: DbSession) -> Sequence[Camera]:
    """Retrieve all cameras ordered by id ascending."""
    return cameras_service.list_cameras(db)


@router.post("", response_model=CameraRead, status_code=status.HTTP_201_CREATED)
def create_camera(camera_in: CameraCreate, db: DbSession) -> Camera:
    """Create a new camera record."""
    return cameras_service.create_camera(db, camera_in)


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
