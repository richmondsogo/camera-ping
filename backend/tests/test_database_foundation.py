import logging
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from tests.conftest import make_test_client
from sqlalchemy import Column, Integer, Table, select
from sqlalchemy.exc import StatementError
from sqlalchemy.orm import Session

from app import clock
from app.config import DEFAULT_DATA_DIR, DEFAULT_DB_PATH, Settings
from app.database import Base, UTCDateTime, create_db_engine, create_sessionmaker
from app.main import create_app


def test_utc_now_timezone_aware() -> None:
    """Ensure clock.utc_now() returns a timezone-aware datetime in UTC."""
    now = clock.utc_now()
    assert now.tzinfo is not None
    assert now.tzinfo == UTC


def test_clock_monkeypatch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that monkeypatching clock.utc_now takes effect as expected."""
    frozen_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    monkeypatch.setattr(clock, "utc_now", lambda: frozen_time)
    assert clock.utc_now() == frozen_time


def test_utc_datetime_type_decorator(tmp_path: Path) -> None:
    """UTCDateTime rejects naive datetimes and returns tz-aware UTC on read."""
    db_file = tmp_path / "type_test.db"
    engine = create_db_engine(f"sqlite:///{db_file.as_posix()}")

    test_table = Table(
        "test_timestamps",
        Base.metadata,
        Column("id", Integer, primary_key=True),
        Column("ts", UTCDateTime, nullable=False),
    )
    test_table.create(engine)

    session_factory = create_sessionmaker(engine)
    session: Session = session_factory()

    # 1. Writing naive datetime must raise StatementError wrapping ValueError
    naive_dt = datetime(2026, 5, 1, 10, 0, 0)
    with pytest.raises(
        StatementError, match="UTCDateTime requires timezone-aware datetime"
    ):
        session.execute(test_table.insert().values(id=1, ts=naive_dt))
        session.commit()
    session.rollback()

    # 2. Writing tz-aware UTC datetime succeeds and returns tz-aware UTC on read
    aware_utc = datetime(2026, 5, 1, 10, 0, 0, tzinfo=UTC)
    session.execute(test_table.insert().values(id=2, ts=aware_utc))
    session.commit()

    stmt = select(test_table.c.ts).where(test_table.c.id == 2)
    row: datetime | None = session.execute(stmt).scalar_one()
    assert row is not None
    assert row.tzinfo is not None
    assert row.tzinfo == UTC
    assert row == aware_utc

    # 3. Writing non-UTC tz-aware datetime converts to UTC on write and returns UTC
    tz_plus_2 = timezone(timedelta(hours=2))
    aware_plus_2 = datetime(2026, 5, 1, 12, 0, 0, tzinfo=tz_plus_2)
    session.execute(test_table.insert().values(id=3, ts=aware_plus_2))
    session.commit()

    stmt3 = select(test_table.c.ts).where(test_table.c.id == 3)
    row3: datetime | None = session.execute(stmt3).scalar_one()
    assert row3 == aware_utc
    assert row3 is not None
    assert row3.tzinfo == UTC

    session.close()
    engine.dispose()


def test_default_db_path_is_absolute_and_cwd_independent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Default DB path is absolute inside backend/data/ independent of cwd."""
    assert DEFAULT_DB_PATH.is_absolute()
    assert DEFAULT_DB_PATH.parent == DEFAULT_DATA_DIR
    assert DEFAULT_DATA_DIR.name == "data"
    assert DEFAULT_DATA_DIR.parent.name == "backend"

    monkeypatch.chdir(tmp_path)
    s = Settings()
    expected_url = f"sqlite:///{DEFAULT_DB_PATH.as_posix()}"
    assert s.database_url == expected_url


def test_in_process_upgrade_preserves_existing_loggers(tmp_path: Path) -> None:
    """Verify that in-process Alembic upgrade does not disable existing loggers."""
    logger_name = "test.camera_monitor.logger"
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)

    records: list[logging.LogRecord] = []

    class ListHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    handler = ListHandler()
    logger.addHandler(handler)

    db_path = tmp_path / "logger_test.db"
    test_settings = Settings(database_url=f"sqlite:///{db_path.as_posix()}")
    test_app = create_app(test_settings)

    with make_test_client(test_app):
        pass

    logger.info("Message after Alembic upgrade")
    assert not logger.disabled
    assert len(records) == 1
    assert records[0].getMessage() == "Message after Alembic upgrade"
