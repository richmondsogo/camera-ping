import sqlite3
from pathlib import Path

import pytest

from app.config import Settings
from app.main import create_app
from tests.conftest import make_test_client


def test_startup_migrates_fresh_database(
    test_settings: Settings, test_db_path: Path
) -> None:
    """Startup lifespan automatically runs migrations on a new SQLite database."""
    app = create_app(test_settings)
    assert not test_db_path.exists()

    with make_test_client(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200

    assert test_db_path.exists()
    conn = sqlite3.connect(test_db_path)
    try:
        tables = [
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        ]
        assert "cameras" in tables
        assert "alembic_version" in tables
    finally:
        conn.close()


def test_startup_fails_on_non_sqlite_file(tmp_path: Path) -> None:
    """Startup lifespan stops and raises RuntimeError if DB file is invalid."""
    bad_db_file = tmp_path / "corrupted.db"
    bad_db_file.write_bytes(b"THIS IS NOT A VALID SQLITE DATABASE FILE HEADER")

    app_settings = Settings(database_url=f"sqlite:///{bad_db_file.as_posix()}")
    app = create_app(app_settings)

    with pytest.raises(RuntimeError) as exc_info:
        with make_test_client(app):
            pass

    error_message = str(exc_info.value)
    assert "Database migration failed at startup" in error_message
    assert str(app_settings.database_url) in error_message


def test_startup_fails_on_unknown_alembic_revision(tmp_path: Path) -> None:
    """Startup lifespan stops and raises RuntimeError if alembic revision is unknown."""
    db_file = tmp_path / "unknown_rev.db"
    conn = sqlite3.connect(db_file)
    try:
        conn.execute(
            "CREATE TABLE alembic_version ("
            "version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
        )
        conn.execute(
            "INSERT INTO alembic_version (version_num) VALUES ('nonexistent_rev_99999')"
        )
        conn.commit()
    finally:
        conn.close()

    app_settings = Settings(database_url=f"sqlite:///{db_file.as_posix()}")
    app = create_app(app_settings)

    with pytest.raises(RuntimeError) as exc_info:
        with make_test_client(app):
            pass

    error_message = str(exc_info.value)
    assert "Database migration failed at startup" in error_message
    assert str(app_settings.database_url) in error_message
