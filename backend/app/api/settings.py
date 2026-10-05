from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.monitoring.engine import MonitoringEngine
from app.schemas.settings import SettingsResponse, SettingsUpdate
from app.services.settings import get_settings, update_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])

DbSession = Annotated[Session, Depends(get_db)]


def _get_engine(request: Request) -> MonitoringEngine:
    engine: MonitoringEngine = request.app.state.monitoring_engine
    return engine


@router.get("", response_model=SettingsResponse)
def read_settings(
    request: Request,
    db: DbSession,
) -> SettingsResponse:
    """Return the effective application settings."""
    app_settings = request.app.state.settings
    return get_settings(db, default_interval=app_settings.monitor_interval_seconds)


@router.patch("", response_model=SettingsResponse)
async def patch_settings(
    request: Request,
    settings_in: SettingsUpdate,
    db: DbSession,
) -> SettingsResponse:
    """Update check interval setting and wake running monitoring engine."""
    engine = _get_engine(request)
    app_settings = request.app.state.settings
    return update_settings(
        db=db,
        settings_in=settings_in,
        engine=engine,
        default_interval=app_settings.monitor_interval_seconds,
    )
