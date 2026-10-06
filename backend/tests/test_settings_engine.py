import asyncio
import threading
import time
from collections.abc import Callable
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy.orm import Session, sessionmaker

from alembic import command
from app import clock
from app.config import BACKEND_DIR
from app.database import create_db_engine, create_sessionmaker
from app.models.camera import Camera
from app.monitoring.engine import MonitoringEngine


def _default_pinger(ip: str) -> bool:
    return True


def _setup_engine(
    tmp_path: Path,
    interval_provider: Callable[[], float],
    pinger: Callable[[str], bool] | None = None,
) -> tuple[MonitoringEngine, sessionmaker[Session]]:
    db_file = tmp_path / "engine_test.db"
    db_url = f"sqlite:///{db_file.as_posix()}"
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(cfg, "head")

    db_engine = create_db_engine(db_url)
    session_factory = create_sessionmaker(db_engine)

    if pinger is None:
        pinger = _default_pinger

    engine = MonitoringEngine(
        session_factory=session_factory,
        pinger=pinger,
        interval=interval_provider,
    )
    return engine, session_factory


def _add_camera(session_factory: sessionmaker[Session], ip: str = "192.0.2.1") -> None:
    now = clock.utc_now()
    with session_factory() as session:
        cam = Camera(
            camera_name="Cam",
            location="HQ",
            description="Test",
            ip_address=ip,
            status="unknown",
            consecutive_failures=0,
            created_at=now,
            updated_at=now,
        )
        session.add(cam)
        session.commit()


@pytest.mark.anyio
async def test_engine_shorter_interval_wakes_and_runs_soon(tmp_path: Path) -> None:
    """When a sleeping scheduler is given a shorter interval, it wakes and runs soon."""
    current_interval = 100.0

    def provider() -> float:
        return current_interval

    cycle_count = 0

    def pinger(ip: str) -> bool:
        nonlocal cycle_count
        cycle_count += 1
        return True

    engine, session_factory = _setup_engine(tmp_path, provider, pinger)
    _add_camera(session_factory)

    try:
        await engine.start()
        # First cycle runs immediately on start
        for _ in range(20):
            if cycle_count == 1:
                break
            await asyncio.sleep(0.05)
        assert cycle_count == 1

        # Now engine is sleeping with 100.0s target
        current_interval = 0.05
        engine.wake()

        # Engine should wake up, re-evaluate remaining time, and run cycle 2 soon
        await asyncio.sleep(0.2)
        assert cycle_count >= 2
    finally:
        await engine.stop()


@pytest.mark.anyio
async def test_engine_longer_interval_does_not_run_at_old_time(
    tmp_path: Path,
) -> None:
    """When given a longer interval, the engine does NOT run at old time."""
    current_interval = 0.15

    def provider() -> float:
        return current_interval

    cycle_count = 0

    def pinger(ip: str) -> bool:
        nonlocal cycle_count
        cycle_count += 1
        return True

    engine, session_factory = _setup_engine(tmp_path, provider, pinger)
    _add_camera(session_factory)

    try:
        await engine.start()
        for _ in range(25):
            if cycle_count >= 1:
                break
            await asyncio.sleep(0.02)
        assert cycle_count == 1

        # Change to a much longer interval (10.0s) and wake
        current_interval = 10.0
        engine.wake()

        # After 0.3s (longer than the old 0.15s interval), cycle 2 should NOT have run
        await asyncio.sleep(0.3)
        assert cycle_count == 1
    finally:
        await engine.stop()


@pytest.mark.anyio
async def test_engine_max_365_days_waits_and_stops_cleanly(tmp_path: Path) -> None:
    """Engine with 365-day interval (31,536,000s) slices wait and stops cleanly."""
    interval_365_days = 31_536_000.0
    engine, session_factory = _setup_engine(tmp_path, lambda: interval_365_days)
    _add_camera(session_factory)

    try:
        await engine.start()
        await asyncio.sleep(0.05)
        assert engine.is_running is True

        # stop() must exit quickly without OverflowError or hanging
        t0 = time.monotonic()
        await engine.stop()
        elapsed = time.monotonic() - t0
        assert elapsed < 1.0
        assert engine.is_running is False
    finally:
        if engine.is_running:
            await engine.stop()


@pytest.mark.anyio
async def test_engine_wake_thread_safe_from_worker_thread(tmp_path: Path) -> None:
    """Scheduler wake-up from a non-event-loop thread wakes scheduler safely."""
    current_interval = 100.0

    def provider() -> float:
        return current_interval

    cycle_count = 0

    def pinger(ip: str) -> bool:
        nonlocal cycle_count
        cycle_count += 1
        return True

    engine, session_factory = _setup_engine(tmp_path, provider, pinger)
    _add_camera(session_factory)

    try:
        await engine.start()
        await asyncio.sleep(0.05)
        assert cycle_count == 1

        # Wake from a background thread
        def worker_trigger() -> None:
            nonlocal current_interval
            current_interval = 0.05
            engine.wake()

        t = threading.Thread(target=worker_trigger)
        t.start()
        t.join()

        # Engine scheduler should wake via call_soon_threadsafe and run cycle 2
        await asyncio.sleep(0.2)
        assert cycle_count >= 2
    finally:
        await engine.stop()


@pytest.mark.anyio
async def test_engine_interval_change_during_in_progress_cycle(
    tmp_path: Path,
) -> None:
    """Interval changes while a cycle is IN PROGRESS; waits with no extra cycle."""
    current_interval = 100.0

    def provider() -> float:
        return current_interval

    cycle_count = 0
    cycle_1_entered = threading.Event()
    unblock_pinger = threading.Event()

    def pinger(ip: str) -> bool:
        nonlocal cycle_count
        cycle_count += 1
        if cycle_count == 1:
            cycle_1_entered.set()
            unblock_pinger.wait(timeout=5.0)
        return True

    engine, session_factory = _setup_engine(tmp_path, provider, pinger)
    _add_camera(session_factory)

    try:
        await engine.start()
        # Wait until cycle 1 is actively inside pinger
        await asyncio.to_thread(cycle_1_entered.wait, 2.0)
        assert cycle_count == 1

        # While cycle 1 is in progress, change interval to 0.25s and wake
        current_interval = 0.25
        engine.wake()

        # Unblock pinger so cycle 1 completes
        unblock_pinger.set()
        await asyncio.sleep(0.05)

        # Immediately after cycle 1 finishes, cycle 2 has NOT run yet (no extra cycle)
        assert cycle_count == 1

        # After the new 0.25s interval elapses, cycle 2 runs
        await asyncio.sleep(0.3)
        assert cycle_count >= 2
    finally:
        unblock_pinger.set()
        await engine.stop()


@pytest.mark.anyio
async def test_wake_before_start_or_after_stop_does_not_start_engine(
    tmp_path: Path,
) -> None:
    """Calling wake before start() or after stop() does not start the engine."""
    engine, session_factory = _setup_engine(tmp_path, lambda: 10.0)
    _add_camera(session_factory)

    # 1. Wake before start
    engine.wake()
    assert engine.is_running is False
    await asyncio.sleep(0.05)
    assert engine.is_running is False

    # 2. Start and then stop
    await engine.start()
    assert engine.is_running is True
    await engine.stop()
    assert engine.is_running is False

    # 3. Wake after stop
    engine.wake()
    assert engine.is_running is False
    await asyncio.sleep(0.05)
    assert engine.is_running is False
