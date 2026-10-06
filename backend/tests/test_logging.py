import asyncio
import logging
import re
from collections.abc import Generator
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from alembic import command
from app import clock
from app.config import BACKEND_DIR
from app.database import create_db_engine, create_sessionmaker
from app.logging_setup import setup_logging
from app.models.camera import Camera
from app.monitoring.engine import MonitoringEngine


@pytest.fixture(autouse=True)
def clean_logging_state() -> Generator[None, None, None]:
    """Reset logging state before and after each logging test."""
    root = logging.getLogger()
    initial_handlers = list(root.handlers)
    old_level = root.level
    try:
        yield
    finally:
        for h in list(root.handlers):
            if h not in initial_handlers:
                root.removeHandler(h)
                try:
                    h.close()
                except Exception:
                    pass
        for h in initial_handlers:
            if h not in root.handlers:
                root.addHandler(h)
        root.setLevel(old_level)
        import app.logging_setup as ls

        ls._logging_configured = False


def _create_db(db_path: Path) -> tuple[sessionmaker[Session], Engine]:
    db_url = f"sqlite:///{db_path.as_posix()}"
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.attributes["skip_logging_config"] = True
    cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(cfg, "head")
    engine = create_db_engine(db_url)
    session_factory = create_sessionmaker(engine)
    return session_factory, engine


def test_logging_setup_rotation_and_format(tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"
    setup_logging(log_dir=log_dir, force=True)

    root = logging.getLogger()
    file_handlers = [h for h in root.handlers if isinstance(h, RotatingFileHandler)]
    assert len(file_handlers) == 1
    fh = file_handlers[0]

    assert fh.maxBytes == 5 * 1024 * 1024
    assert fh.backupCount == 5
    assert fh.encoding == "utf-8"
    assert (log_dir / "camera-monitor.log").exists()

    test_logger = logging.getLogger("test_logger")
    test_logger.info("Test message 123")
    fh.flush()

    content = (log_dir / "camera-monitor.log").read_text(encoding="utf-8")
    assert re.search(
        r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} INFO test_logger Test message 123",
        content,
    )


def test_logging_setup_idempotent(tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"
    setup_logging(log_dir=log_dir, force=True)
    root = logging.getLogger()
    initial_handlers = list(root.handlers)

    # Second call without force must be a no-op
    setup_logging(log_dir=log_dir, force=False)
    assert root.handlers == initial_handlers


def test_logging_unicode_camera_name(tmp_path: Path) -> None:
    """Amendment 3: Unicode camera name logs to both handlers without error."""
    log_dir = tmp_path / "logs"
    setup_logging(log_dir=log_dir, force=True)

    root = logging.getLogger()
    camera_name = "Café Ñandú 入口"
    log_msg = f"Camera '{camera_name}' (192.0.2.10) is ONLINE"

    logging.getLogger("app.monitoring.engine").info(log_msg)

    for h in root.handlers:
        h.flush()

    content = (log_dir / "camera-monitor.log").read_text(encoding="utf-8")
    assert camera_name in content


def test_engine_status_transition_logging(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Engine logs at INFO only when status changes; unchanged logs nothing."""
    session_factory, engine = _create_db(tmp_path / "test.db")
    now = clock.utc_now()

    with session_factory() as s:
        cam1 = Camera(
            camera_name="Cam 1",
            location="HQ",
            description="",
            ip_address="192.0.2.1",
            status="unknown",
            created_at=now,
            updated_at=now,
        )
        cam2 = Camera(
            camera_name="Cam 2",
            location="HQ",
            description="",
            ip_address="192.0.2.2",
            status="unknown",
            created_at=now,
            updated_at=now,
        )
        s.add_all([cam1, cam2])
        s.commit()

    # Cycle 1: Cam 1 online, Cam 2 offline (transitions from UNKNOWN)
    probe_results = {"192.0.2.1": True, "192.0.2.2": False}
    mon_engine = MonitoringEngine(
        session_factory=session_factory, pinger=lambda ip: probe_results[ip]
    )

    with caplog.at_level(logging.INFO):
        caplog.clear()
        mon_engine.run_cycle_sync()

    records = [
        r.getMessage() for r in caplog.records if r.name == "app.monitoring.engine"
    ]
    assert "Camera 'Cam 1' (192.0.2.1) is ONLINE" in records
    assert "Camera 'Cam 2' (192.0.2.2) is OFFLINE" in records

    # Cycle 2: Unchanged statuses (Cam 1 online, Cam 2 offline) -> MUST LOG NOTHING
    with caplog.at_level(logging.INFO):
        caplog.clear()
        mon_engine.run_cycle_sync()

    records = [
        r.getMessage() for r in caplog.records if r.name == "app.monitoring.engine"
    ]
    assert not any("Cam 1" in r or "Cam 2" in r for r in records)

    # Cycle 3: Cam 1 goes OFFLINE, Cam 2 goes ONLINE after failed checks
    probe_results["192.0.2.1"] = False
    probe_results["192.0.2.2"] = True
    with caplog.at_level(logging.INFO):
        caplog.clear()
        mon_engine.run_cycle_sync()

    records = [
        r.getMessage() for r in caplog.records if r.name == "app.monitoring.engine"
    ]
    assert "Camera 'Cam 1' (192.0.2.1) went OFFLINE" in records
    assert "Camera 'Cam 2' (192.0.2.2) back ONLINE after 2 failed checks" in records

    engine.dispose()


def test_engine_start_stop_logs(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    session_factory, engine = _create_db(tmp_path / "test.db")
    mon_engine = MonitoringEngine(
        session_factory=session_factory, pinger=lambda ip: True, interval=60.0
    )

    async def _run() -> None:
        await mon_engine.start()
        await mon_engine.stop()

    with caplog.at_level(logging.INFO):
        caplog.clear()
        asyncio.run(_run())

    records = [
        r.getMessage() for r in caplog.records if r.name == "app.monitoring.engine"
    ]
    assert "Monitoring engine started" in records
    assert "Monitoring engine stopped" in records

    engine.dispose()


def test_engine_cycle_overrun_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    session_factory, engine = _create_db(tmp_path / "test.db")
    mon_engine = MonitoringEngine(
        session_factory=session_factory, pinger=lambda ip: True, interval=0.01
    )

    def slow_run() -> None:
        import time

        time.sleep(0.05)

    mon_engine.run_cycle_sync = slow_run  # type: ignore[method-assign]

    async def _run() -> None:
        mon_engine._stop_event.clear()
        task = asyncio.create_task(mon_engine._scheduler_loop())
        await asyncio.sleep(0.08)
        mon_engine._stop_event.set()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    with caplog.at_level(logging.WARNING):
        caplog.clear()
        asyncio.run(_run())

    records = [
        r.getMessage()
        for r in caplog.records
        if r.name == "app.monitoring.engine" and r.levelno == logging.WARNING
    ]
    assert any("exceeding configured interval" in r for r in records)

    engine.dispose()


def test_engine_cycle_exception_logged(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    session_factory, engine = _create_db(tmp_path / "test.db")
    mon_engine = MonitoringEngine(
        session_factory=session_factory, pinger=lambda ip: True, interval=60.0
    )

    def failing_run() -> None:
        raise RuntimeError("Simulated database failure")

    mon_engine.run_cycle_sync = failing_run  # type: ignore[method-assign]

    async def _run() -> None:
        mon_engine._stop_event.clear()
        task = asyncio.create_task(mon_engine._scheduler_loop())
        await asyncio.sleep(0.05)
        mon_engine._stop_event.set()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    with caplog.at_level(logging.ERROR):
        caplog.clear()
        asyncio.run(_run())

    records = [
        r
        for r in caplog.records
        if r.name == "app.monitoring.engine" and r.levelno == logging.ERROR
    ]
    assert len(records) >= 1
    assert "Unexpected error in monitoring cycle execution" in records[0].getMessage()
    assert records[0].exc_info is not None

    engine.dispose()


def test_alembic_logger_silenced_to_warning(tmp_path: Path) -> None:
    """Alembic plugin and migration discovery messages are silenced to WARNING."""
    setup_logging(log_dir=tmp_path / "logs", force=True)
    alembic_logger = logging.getLogger("alembic")
    assert alembic_logger.level == logging.WARNING
