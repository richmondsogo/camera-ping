from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.config import DEFAULT_DATA_DIR, Settings
from app.main import create_app


@pytest.fixture(autouse=True)
def guard_data_directory() -> Generator[None, None, None]:
    """Autouse guard ensuring tests never create, modify, or touch backend/data/."""

    def get_snapshot() -> tuple[bool, list[str]]:
        if not DEFAULT_DATA_DIR.exists():
            return (False, [])
        return (True, sorted(f.name for f in DEFAULT_DATA_DIR.iterdir()))

    before_exists, before_files = get_snapshot()
    yield
    after_exists, after_files = get_snapshot()

    if before_exists != after_exists or before_files != after_files:
        raise AssertionError(
            f"Test touched production data directory {DEFAULT_DATA_DIR}! "
            f"Before: exists={before_exists}, files={before_files}; "
            f"After: exists={after_exists}, files={after_files}"
        )


@pytest.fixture
def test_db_path(tmp_path: Path) -> Path:
    """Provide a unique temporary SQLite database file path per test."""
    return tmp_path / "test_camera_monitor.db"


@pytest.fixture
def test_settings(test_db_path: Path) -> Settings:
    """Provide test settings pointing to the temporary SQLite database file."""
    return Settings(database_url=f"sqlite:///{test_db_path.as_posix()}")


@pytest.fixture
def app_instance(test_settings: Settings) -> FastAPI:
    """Create a FastAPI application instance configured for this test function."""
    return create_app(test_settings)


def make_test_client(app: FastAPI, **kwargs: object) -> TestClient:
    """Create a TestClient with base_url defaulting to http://localhost."""
    kwargs.setdefault("base_url", "http://localhost")
    return TestClient(app, **kwargs)  # type: ignore[arg-type]


@pytest.fixture
def client(app_instance: FastAPI) -> Generator[TestClient, None, None]:
    """TestClient that runs app lifespan (migrating tmp_path database)."""
    with make_test_client(app_instance) as test_client:
        yield test_client


@pytest.fixture
def db_session(
    app_instance: FastAPI, client: TestClient
) -> Generator[Session, None, None]:
    """Provide a test database session bound to the test application's engine."""
    session_factory: sessionmaker[Session] = app_instance.state.sessionmaker
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
