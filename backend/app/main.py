from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from alembic.config import Config
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import Engine

from alembic import command
from app.api.cameras import router as cameras_router
from app.api.health import router as health_router
from app.config import BACKEND_DIR, Settings, settings
from app.database import create_db_engine, create_sessionmaker
from app.exceptions import CameraNotFoundError, DuplicateIpError
from app.models.monitoring import MonitoringState
from app.monitoring.engine import MonitoringEngine
from app.monitoring.probe import ping_host


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    """FastAPI application lifespan manager.

    Creates data directory on startup if using SQLite, runs Alembic migrations to head,
    resumes monitoring engine if previously running, cancels monitoring on shutdown
    without mutating the persisted flag, and cleanly disposes the database engine.
    """
    app_settings: Settings = application.state.settings

    if app_settings.database_url.startswith("sqlite"):
        db_path_str = app_settings.database_url.replace("sqlite:///", "")
        db_path = Path(db_path_str)
        try:
            db_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            msg = (
                f"Failed to create database directory {db_path.parent} "
                f"for {app_settings.database_url}: {e}"
            )
            raise RuntimeError(msg) from e

    alembic_ini_path = BACKEND_DIR / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini_path))
    alembic_cfg.set_main_option("sqlalchemy.url", app_settings.database_url)

    try:
        command.upgrade(alembic_cfg, "head")
    except Exception as e:
        msg = (
            f"Database migration failed at startup for database file "
            f"{app_settings.database_url}: {e}"
        )
        raise RuntimeError(msg) from e

    session_factory = application.state.sessionmaker
    with session_factory() as session:
        state = session.get(MonitoringState, 1)
        should_resume = state.running if state is not None else False

    if should_resume:
        await application.state.monitoring_engine.start()

    yield

    await application.state.monitoring_engine.shutdown()

    engine: Engine = application.state.engine
    engine.dispose()


def create_app(
    app_settings: Settings | None = None,
    pinger: Callable[[str], bool] | None = None,
) -> FastAPI:
    """Application factory for Camera Monitor.

    Builds the database engine and sessionmaker, stores them on app.state,
    registers routers, exception handlers, engine, and startup lifespan.
    """
    if app_settings is None:
        app_settings = settings

    if pinger is None:
        pinger = ping_host

    application = FastAPI(
        title="Camera Monitor API",
        version="0.1.0",
        lifespan=lifespan,
    )

    engine = create_db_engine(app_settings.database_url)
    session_factory = create_sessionmaker(engine)
    monitoring_engine = MonitoringEngine(
        session_factory=session_factory,
        pinger=pinger,
        interval=app_settings.monitor_interval_seconds,
    )

    application.state.settings = app_settings
    application.state.engine = engine
    application.state.sessionmaker = session_factory
    application.state.monitoring_engine = monitoring_engine

    @application.exception_handler(CameraNotFoundError)
    async def camera_not_found_handler(
        request: Request, exc: CameraNotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={"detail": "Camera not found."},
        )

    @application.exception_handler(DuplicateIpError)
    async def duplicate_ip_handler(
        request: Request, exc: DuplicateIpError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={
                "detail": [
                    {
                        "loc": ["body", "ip_address"],
                        "msg": "A camera with this IP address already exists.",
                        "type": "duplicate",
                    }
                ]
            },
        )

    application.include_router(health_router)
    application.include_router(cameras_router)

    return application


# Module-level instance for uvicorn
app = create_app()
