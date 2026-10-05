from sqlalchemy.orm import Session

from app.models.setting import AppSettings
from app.monitoring.engine import MonitoringEngine
from app.schemas.settings import SettingsResponse, SettingsUpdate


def get_effective_interval(db: Session, default_interval: int) -> int:
    """Return stored check interval if set, otherwise the environment default."""
    setting = db.get(AppSettings, 1)
    if setting is not None and setting.check_interval_seconds is not None:
        return setting.check_interval_seconds
    return default_interval


def get_settings(db: Session, default_interval: int) -> SettingsResponse:
    """Return effective application settings."""
    effective = get_effective_interval(db, default_interval)
    return SettingsResponse(check_interval_seconds=effective)


def update_settings(
    db: Session,
    settings_in: SettingsUpdate,
    engine: MonitoringEngine,
    default_interval: int,
) -> SettingsResponse:
    """Update check interval in database and wake running scheduler."""
    setting = db.get(AppSettings, 1)
    if setting is None:
        setting = AppSettings(
            id=1,
            check_interval_seconds=settings_in.check_interval_seconds,
        )
        db.add(setting)
    else:
        setting.check_interval_seconds = settings_in.check_interval_seconds

    db.commit()
    db.refresh(setting)

    # Wake running scheduler so new interval applies immediately
    engine.wake()

    effective = get_effective_interval(db, default_interval)
    return SettingsResponse(check_interval_seconds=effective)
