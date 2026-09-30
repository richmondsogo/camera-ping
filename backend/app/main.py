from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from alembic.config import Config
from fastapi import FastAPI
from sqlalchemy import Engine

from alembic import command
from app.api.health import router as health_router
from app.config import BACKEND_DIR, Settings, settings
from app.database import create_db_engine, create_sessionmaker


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    """FastAPI application lifespan manager.

    Creates data directory on startup if using SQLite, runs Alembic migrations to head,
    and cleanly disposes the database engine on shutdown.
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

    yield

    engine: Engine = application.state.engine
    engine.dispose()


def create_app(app_settings: Settings | None = None) -> FastAPI:
    """Application factory for Camera Monitor.

    Builds the database engine and sessionmaker, stores them on app.state,
    and registers routers and the startup lifespan.
    """
    if app_settings is None:
        app_settings = settings

    application = FastAPI(
        title="Camera Monitor API",
        version="0.1.0",
        lifespan=lifespan,
    )

    engine = create_db_engine(app_settings.database_url)
    session_factory = create_sessionmaker(engine)

    application.state.settings = app_settings
    application.state.engine = engine
    application.state.sessionmaker = session_factory

    application.include_router(health_router)

    return application


# Module-level instance for uvicorn
app = create_app()
