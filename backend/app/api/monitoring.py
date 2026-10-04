from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.monitoring.engine import MonitoringEngine
from app.schemas.monitoring import MonitoringStatusResponse

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])

DbSession = Annotated[Session, Depends(get_db)]


def _get_engine(request: Request) -> MonitoringEngine:
    engine: MonitoringEngine = request.app.state.monitoring_engine
    return engine


@router.get("/status", response_model=MonitoringStatusResponse)
def get_monitoring_status(
    request: Request,
    db: DbSession,
) -> MonitoringStatusResponse:
    """Return the current monitoring status and camera reachability counts."""
    engine = _get_engine(request)
    status_info = engine.get_status(db=db)
    return MonitoringStatusResponse.model_validate(status_info)


@router.post("/start", response_model=MonitoringStatusResponse)
async def start_monitoring(
    request: Request,
    db: DbSession,
) -> MonitoringStatusResponse:
    """Start periodic monitoring and return status without waiting for the cycle."""
    engine = _get_engine(request)
    await engine.start()
    status_info = engine.get_status(db=db)
    return MonitoringStatusResponse.model_validate(status_info)


@router.post("/stop", response_model=MonitoringStatusResponse)
async def stop_monitoring(
    request: Request,
    db: DbSession,
) -> MonitoringStatusResponse:
    """Stop periodic monitoring, discard in-flight results, and return status."""
    engine = _get_engine(request)
    await engine.stop()
    status_info = engine.get_status(db=db)
    return MonitoringStatusResponse.model_validate(status_info)
