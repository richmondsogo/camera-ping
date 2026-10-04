import asyncio
import threading
import time
from datetime import datetime
from pathlib import Path

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from alembic import command
from app import clock
from app.config import BACKEND_DIR, Settings
from app.database import create_db_engine, create_sessionmaker
from app.main import create_app
from app.models.camera import Camera, CameraStatus
from app.models.monitoring import MonitoringState
from app.monitoring.engine import MonitoringEngine


def _create_migrated_db(db_path: Path) -> tuple[sessionmaker[Session], Engine]:
    db_url = f"sqlite:///{db_path.as_posix()}"
    alembic_ini_path = BACKEND_DIR / "alembic.ini"
    cfg = Config(str(alembic_ini_path))
    cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(cfg, "head")

    engine = create_db_engine(db_url)
    session_factory = create_sessionmaker(engine)
    return session_factory, engine


def _add_camera(
    session: Session,
    ip: str,
    name: str = "Cam",
    status: str = "unknown",
    consecutive_failures: int = 0,
    last_online: datetime | None = None,
) -> Camera:
    now = clock.utc_now()
    cam = Camera(
        camera_name=name,
        location="HQ",
        description="Test camera",
        ip_address=ip,
        status=status,
        consecutive_failures=consecutive_failures,
        last_online=last_online,
        created_at=now,
        updated_at=now,
    )
    session.add(cam)
    session.commit()
    session.refresh(cam)
    return cam


# 1. Rule transitions
def test_rule_transitions(tmp_path: Path) -> None:
    db_path = tmp_path / "rules.db"
    session_factory, engine = _create_migrated_db(db_path)

    with session_factory() as session:
        cam = _add_camera(session, "192.0.2.10", status="unknown")
        assert cam.status == "unknown"
        assert cam.consecutive_failures == 0
        assert cam.last_online is None
        assert cam.last_checked is None

    # Cycle 1: Probe success -> online
    engine_mon = MonitoringEngine(session_factory, pinger=lambda ip: True)
    engine_mon.run_cycle_sync()

    with session_factory() as session:
        cam_db = session.get(Camera, 1)
        assert cam_db is not None
        assert cam_db.status == CameraStatus.ONLINE
        assert cam_db.consecutive_failures == 0
        assert cam_db.last_online is not None
        assert cam_db.last_checked is not None
        first_online_time = cam_db.last_online

    # Cycle 2: Probe failure -> offline
    engine_mon.pinger = lambda ip: False
    engine_mon.run_cycle_sync()

    with session_factory() as session:
        cam_db2 = session.get(Camera, 1)
        assert cam_db2 is not None
        assert cam_db2.status == CameraStatus.OFFLINE
        assert cam_db2.consecutive_failures == 1
        assert cam_db2.last_online == first_online_time
        assert cam_db2.last_checked is not None
        assert cam_db2.last_checked > first_online_time

    engine.dispose()


# 2. Failure streaks
def test_failure_streaks_and_reset(tmp_path: Path) -> None:
    db_path = tmp_path / "streaks.db"
    session_factory, engine = _create_migrated_db(db_path)

    with session_factory() as session:
        _add_camera(session, "192.0.2.10", status="unknown")

    engine_mon = MonitoringEngine(session_factory, pinger=lambda ip: False)

    for i in range(1, 11):
        engine_mon.run_cycle_sync()
        with session_factory() as session:
            cam = session.get(Camera, 1)
            assert cam is not None
            assert cam.status == CameraStatus.OFFLINE
            assert cam.consecutive_failures == i

    # Next cycle succeeds -> streak reset to 0, status online
    engine_mon.pinger = lambda ip: True
    engine_mon.run_cycle_sync()

    with session_factory() as session:
        cam_reset = session.get(Camera, 1)
        assert cam_reset is not None
        assert cam_reset.status == CameraStatus.ONLINE
        assert cam_reset.consecutive_failures == 0
        assert cam_reset.last_online is not None

    engine.dispose()


# 3. Restart persistence
def test_streak_persistence_across_restart(tmp_path: Path) -> None:
    db_path = tmp_path / "restart.db"
    session_factory, engine = _create_migrated_db(db_path)

    with session_factory() as session:
        _add_camera(
            session,
            "192.0.2.10",
            status="offline",
            consecutive_failures=7,
        )
    engine.dispose()

    # Recreate engine and session_factory pointing to existing DB
    engine2 = create_db_engine(f"sqlite:///{db_path.as_posix()}")
    session_factory2 = create_sessionmaker(engine2)

    engine_mon = MonitoringEngine(session_factory2, pinger=lambda ip: False)
    engine_mon.run_cycle_sync()

    with session_factory2() as session:
        cam = session.get(Camera, 1)
        assert cam is not None
        assert cam.status == CameraStatus.OFFLINE
        assert cam.consecutive_failures == 8

    engine2.dispose()


# 4. Running flag persistence across app restart
def test_running_flag_persistence_across_app_restart(tmp_path: Path) -> None:
    db_path = tmp_path / "flag_persistence.db"
    settings = Settings(database_url=f"sqlite:///{db_path.as_posix()}")

    # App 1: Start monitoring via POST /api/monitoring/start
    app1 = create_app(settings, pinger=lambda ip: True)
    with TestClient(app1) as client1:
        res = client1.post("/api/monitoring/start")
        assert res.status_code == 200
        assert res.json()["running"] is True

    # After app1 shuts down, DB must still record running = 1
    engine = create_db_engine(f"sqlite:///{db_path.as_posix()}")
    session_factory = create_sessionmaker(engine)
    with session_factory() as session:
        state = session.get(MonitoringState, 1)
        assert state is not None
        assert state.running is True
    engine.dispose()

    # App 2: Startup should automatically resume monitoring because DB was running
    app2 = create_app(settings, pinger=lambda ip: True)
    with TestClient(app2) as client2:
        status_res = client2.get("/api/monitoring/status")
        assert status_res.status_code == 200
        assert status_res.json()["running"] is True

        # Now explicitly stop monitoring
        stop_res = client2.post("/api/monitoring/stop")
        assert stop_res.status_code == 200
        assert stop_res.json()["running"] is False

    # App 3: Startup should stay stopped because running was set to False
    app3 = create_app(settings, pinger=lambda ip: True)
    with TestClient(app3) as client3:
        status_res3 = client3.get("/api/monitoring/status")
        assert status_res3.status_code == 200
        assert status_res3.json()["running"] is False


# 5. Scheduler mechanics
@pytest.mark.anyio
async def test_scheduler_mechanics_start_stop_idempotency(tmp_path: Path) -> None:
    db_path = tmp_path / "sched.db"
    session_factory, engine = _create_migrated_db(db_path)

    with session_factory() as session:
        _add_camera(session, "192.0.2.10")

    cycle_count = 0

    def pinger(ip: str) -> bool:
        nonlocal cycle_count
        cycle_count += 1
        return True

    engine_mon = MonitoringEngine(session_factory, pinger=pinger, interval=0.05)

    # Idempotent start
    await engine_mon.start()
    await engine_mon.start()
    assert engine_mon.is_running is True

    # Wait briefly for cycles
    await asyncio.sleep(0.12)
    assert cycle_count >= 1

    # Idempotent stop
    await engine_mon.stop()
    await engine_mon.stop()
    assert engine_mon.is_running is False

    count_after_stop = cycle_count
    await asyncio.sleep(0.15)
    # No more cycles should run after stop
    assert cycle_count == count_after_stop

    engine.dispose()


@pytest.mark.anyio
async def test_scheduler_stop_mid_cycle_discards_results(tmp_path: Path) -> None:
    db_path = tmp_path / "mid_cycle.db"
    session_factory, engine = _create_migrated_db(db_path)

    with session_factory() as session:
        _add_camera(session, "192.0.2.10", status="unknown")

    in_probe_event = threading.Event()
    release_probe_event = threading.Event()

    def blocked_pinger(ip: str) -> bool:
        in_probe_event.set()
        release_probe_event.wait(timeout=2.0)
        return True

    engine_mon = MonitoringEngine(session_factory, pinger=blocked_pinger, interval=1.0)
    start_task = asyncio.create_task(engine_mon.start())

    # Wait until probe starts
    await asyncio.to_thread(in_probe_event.wait, 2.0)
    assert in_probe_event.is_set()

    # Now request stop while probe is in flight
    await engine_mon.stop()

    # Release blocked probe
    release_probe_event.set()
    await start_task

    # Status must NOT have been applied to DB
    with session_factory() as session:
        cam = session.get(Camera, 1)
        assert cam is not None
        assert cam.status == "unknown"
        assert cam.last_checked is None

    engine.dispose()


def test_unexpected_probe_exception_handled(tmp_path: Path) -> None:
    db_path = tmp_path / "probe_exc.db"
    session_factory, engine = _create_migrated_db(db_path)

    with session_factory() as session:
        _add_camera(session, "192.0.2.10")

    def error_pinger(ip: str) -> bool:
        raise RuntimeError("Network stack crash")

    engine_mon = MonitoringEngine(session_factory, pinger=error_pinger)
    # Must not raise
    engine_mon.run_cycle_sync()

    with session_factory() as session:
        cam = session.get(Camera, 1)
        assert cam is not None
        assert cam.status == CameraStatus.OFFLINE
        assert cam.consecutive_failures == 1

    engine.dispose()


# 6. Concurrency & Performance
def test_concurrency_and_performance(tmp_path: Path) -> None:
    db_path = tmp_path / "perf.db"
    session_factory, engine = _create_migrated_db(db_path)

    with session_factory() as session:
        for i in range(30):
            _add_camera(session, f"192.0.2.{i + 1}", name=f"Cam-{i + 1}")

    def slow_pinger(ip: str) -> bool:
        time.sleep(0.2)
        return True

    engine_mon = MonitoringEngine(session_factory, pinger=slow_pinger)

    start_time = time.monotonic()
    engine_mon.run_cycle_sync()
    duration = time.monotonic() - start_time

    # 30 cameras * 0.2s = 6.0s sequential, should easily finish < 1.5s with concurrency
    assert duration < 1.5, f"Cycle took {duration:.2f}s, expected < 1.5s"

    engine.dispose()


def test_worker_thread_pool_capped_at_32(tmp_path: Path) -> None:
    db_path = tmp_path / "cap.db"
    session_factory, engine = _create_migrated_db(db_path)

    with session_factory() as session:
        for i in range(60):
            _add_camera(session, f"192.0.2.{i + 1}", name=f"Cam-{i + 1}")

    lock = threading.Lock()
    active_workers = 0
    max_active_workers = 0

    def tracking_pinger(ip: str) -> bool:
        nonlocal active_workers, max_active_workers
        with lock:
            active_workers += 1
            if active_workers > max_active_workers:
                max_active_workers = active_workers
        time.sleep(0.05)
        with lock:
            active_workers -= 1
        return True

    engine_mon = MonitoringEngine(session_factory, pinger=tracking_pinger)
    engine_mon.run_cycle_sync()

    assert max_active_workers <= 32
    assert max_active_workers > 1

    engine.dispose()


# 7. Isolation & Concurrency safety
def test_isolation_camera_renamed_preserved(tmp_path: Path) -> None:
    db_path = tmp_path / "rename.db"
    session_factory, engine = _create_migrated_db(db_path)

    with session_factory() as session:
        _add_camera(session, "192.0.2.10", name="Original Name")

    def renaming_pinger(ip: str) -> bool:
        # Simulate user renaming camera concurrently during probe execution
        with session_factory() as s:
            c = s.get(Camera, 1)
            assert c is not None
            c.camera_name = "Renamed Name"
            s.commit()
        return True

    engine_mon = MonitoringEngine(session_factory, pinger=renaming_pinger)
    engine_mon.run_cycle_sync()

    with session_factory() as session:
        cam = session.get(Camera, 1)
        assert cam is not None
        assert cam.camera_name == "Renamed Name"
        assert cam.status == CameraStatus.ONLINE

    engine.dispose()


def test_isolation_camera_ip_changed_discards_stale_result(tmp_path: Path) -> None:
    db_path = tmp_path / "ip_change.db"
    session_factory, engine = _create_migrated_db(db_path)

    with session_factory() as session:
        _add_camera(session, "192.0.2.10", status="unknown")

    def ip_changing_pinger(ip: str) -> bool:
        # Simulate user changing IP concurrently during probe execution
        with session_factory() as s:
            c = s.get(Camera, 1)
            assert c is not None
            c.ip_address = "192.0.2.20"
            s.commit()
        return True

    engine_mon = MonitoringEngine(session_factory, pinger=ip_changing_pinger)
    engine_mon.run_cycle_sync()

    with session_factory() as session:
        cam = session.get(Camera, 1)
        assert cam is not None
        # Stale probe of 192.0.2.10 must be discarded; camera remains unknown
        assert cam.status == "unknown"
        assert cam.last_checked is None

    engine.dispose()


def test_isolation_camera_deleted_during_cycle_handled(tmp_path: Path) -> None:
    db_path = tmp_path / "deleted.db"
    session_factory, engine = _create_migrated_db(db_path)

    with session_factory() as session:
        _add_camera(session, "192.0.2.10")

    def deleting_pinger(ip: str) -> bool:
        with session_factory() as s:
            c = s.get(Camera, 1)
            if c:
                s.delete(c)
                s.commit()
        return True

    engine_mon = MonitoringEngine(session_factory, pinger=deleting_pinger)
    # Must not raise an error
    engine_mon.run_cycle_sync()

    with session_factory() as session:
        cam = session.get(Camera, 1)
        assert cam is None

    engine.dispose()


def test_isolation_updated_at_untouched_by_cycle(tmp_path: Path) -> None:
    db_path = tmp_path / "updated_at.db"
    session_factory, engine = _create_migrated_db(db_path)

    with session_factory() as session:
        cam = _add_camera(session, "192.0.2.10")
        original_updated_at = cam.updated_at

    engine_mon = MonitoringEngine(session_factory, pinger=lambda ip: True)
    engine_mon.run_cycle_sync()

    with session_factory() as session:
        cam_db = session.get(Camera, 1)
        assert cam_db is not None
        assert cam_db.status == CameraStatus.ONLINE
        assert cam_db.updated_at == original_updated_at

    engine.dispose()


# 8. Thread isolation test (User amendment 3)
def test_thread_isolation_no_sqlite_objects_shared(tmp_path: Path) -> None:
    """Only ping_host runs in ThreadPoolExecutor; every DB operation uses a session

    created in the calling thread. No SQLite thread-check errors occur.
    """
    db_path = tmp_path / "thread_iso.db"
    session_factory, engine = _create_migrated_db(db_path)

    with session_factory() as session:
        for i in range(30):
            _add_camera(session, f"192.0.2.{i + 1}", name=f"Cam-{i + 1}")

    def pinger(ip: str) -> bool:
        # Verify pinger executes in a thread without accessing any DB objects
        time.sleep(0.01)
        return True

    engine_mon = MonitoringEngine(session_factory, pinger=pinger)
    # Run cycle on file database with 30 cameras
    engine_mon.run_cycle_sync()

    with session_factory() as session:
        cams = session.execute(select(Camera)).scalars().all()
        assert len(cams) == 30
        for cam in cams:
            assert cam.status == CameraStatus.ONLINE

    engine.dispose()


# 9. API endpoint tests & hidden fields absent
def test_monitoring_api_endpoints_and_hidden_fields_absent(tmp_path: Path) -> None:
    db_path = tmp_path / "api_test.db"
    settings = Settings(database_url=f"sqlite:///{db_path.as_posix()}")

    app = create_app(settings, pinger=lambda ip: True)
    with TestClient(app) as client:
        # GET /api/monitoring/status initial
        res = client.get("/api/monitoring/status")
        assert res.status_code == 200
        data = res.json()
        assert data["running"] is False
        assert data["interval_seconds"] == settings.monitor_interval_seconds
        assert data["total"] == 0
        assert data["online"] == 0
        assert data["offline"] == 0
        assert data["unknown"] == 0
        assert data["next_check_at"] is None

        # Verify hidden / internal fields are ABSENT
        assert "consecutive_failures" not in data
        assert "alert_sent_for_current_outage" not in data
        assert "alert_sent" not in data
        assert "alert" not in data

        # POST /api/monitoring/start
        start_res = client.post("/api/monitoring/start")
        assert start_res.status_code == 200
        start_data = start_res.json()
        assert start_data["running"] is True
        assert "consecutive_failures" not in start_data
        assert "alert_sent_for_current_outage" not in start_data

        # POST /api/monitoring/stop
        stop_res = client.post("/api/monitoring/stop")
        assert stop_res.status_code == 200
        stop_data = stop_res.json()
        assert stop_data["running"] is False
        assert "consecutive_failures" not in stop_data
        assert "alert_sent_for_current_outage" not in stop_data
