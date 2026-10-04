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
        assert data["running_since"] is None

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
        assert start_data["running_since"] is not None
        assert "consecutive_failures" not in start_data
        assert "alert_sent_for_current_outage" not in start_data

        # POST /api/monitoring/stop
        stop_res = client.post("/api/monitoring/stop")
        assert stop_res.status_code == 200
        stop_data = stop_res.json()
        assert stop_data["running"] is False
        assert stop_data["running_since"] is None
        assert "consecutive_failures" not in stop_data
        assert "alert_sent_for_current_outage" not in stop_data


# 10. Checkpoint 1: running_since and next_check_at behavior
def test_running_since_and_next_check_at_behavior(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """next_check_at is null right after start, set after first cycle."""

    async def _run() -> None:
        db_path = tmp_path / "timing.db"
        session_factory, engine_db = _create_migrated_db(db_path)

        t0 = datetime(2026, 10, 1, 10, 0, 0, tzinfo=clock.UTC)
        t1 = datetime(2026, 10, 1, 10, 0, 10, tzinfo=clock.UTC)

        monkeypatch.setattr(clock, "utc_now", lambda: t0)

        engine = MonitoringEngine(
            session_factory, pinger=lambda ip: True, interval=60.0
        )

        # 1. Stopped initially: running_since is None, next_check_at is None
        status0 = engine.get_status()
        assert status0.running is False
        assert status0.running_since is None
        assert status0.next_check_at is None

        # 2. Hold cycle lock so cycle 1 cannot begin immediately
        engine._cycle_lock.acquire()
        try:
            await engine.start()
            status1 = engine.get_status()
            assert status1.running is True
            assert status1.running_since == t0
            assert status1.next_check_at is None
        finally:
            if engine._cycle_lock.locked():
                engine._cycle_lock.release()

        # 3. Allow cycle 1 to run
        monkeypatch.setattr(clock, "utc_now", lambda: t1)
        await asyncio.sleep(0.1)

        status2 = engine.get_status()
        assert status2.running is True
        assert status2.running_since == t0
        assert status2.last_cycle_started_at is not None
        assert status2.next_check_at is not None

        # 4. Stop: running_since cleared to None, next_check_at is None
        await engine.stop()
        status3 = engine.get_status()
        assert status3.running is False
        assert status3.running_since is None
        assert status3.next_check_at is None

        engine_db.dispose()

    asyncio.run(_run())


# 11. Checkpoint 1: Resume at startup sets running_since and avoids stale next_check_at
def test_resume_at_startup_sets_running_since_and_nulls_stale_next_check_at(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Resume at startup sets running_since; next_check_at is null before cycle 1."""
    db_path = tmp_path / "resume_timing.db"
    session_factory, engine_db = _create_migrated_db(db_path)

    # Seed state in DB from a previous run
    old_time = datetime(2026, 10, 1, 8, 0, 0, tzinfo=clock.UTC)
    with session_factory() as session:
        state = session.get(MonitoringState, 1)
        assert state is not None
        state.running = True
        state.last_cycle_started_at = old_time
        state.last_cycle_finished_at = old_time
        session.commit()

    startup_time = datetime(2026, 10, 1, 12, 0, 0, tzinfo=clock.UTC)
    monkeypatch.setattr(clock, "utc_now", lambda: startup_time)

    settings = Settings(database_url=f"sqlite:///{db_path.as_posix()}")
    app = create_app(settings, pinger=lambda ip: True)

    app.state.monitoring_engine._cycle_lock.acquire()
    try:
        with TestClient(app) as client:
            # Upon startup, engine resumed but cycle 1 is blocked by cycle_lock
            res = client.get("/api/monitoring/status")
            assert res.status_code == 200
            data = res.json()
            assert data["running"] is True
            assert datetime.fromisoformat(data["running_since"]) == startup_time
            # Because old_time < startup_time, next_check_at must NOT be stale
            assert data["next_check_at"] is None

            # Release the lock so cycle 1 can proceed
            app.state.monitoring_engine._cycle_lock.release()
            time.sleep(0.1)

            res2 = client.get("/api/monitoring/status")
            data2 = res2.json()
            assert data2["next_check_at"] is not None

            # Clean shutdown by stopping
            client.post("/api/monitoring/stop")
    finally:
        if app.state.monitoring_engine._cycle_lock.locked():
            app.state.monitoring_engine._cycle_lock.release()

    engine_db.dispose()


# 12. Checkpoint 1: consecutive_failures counting and reset via API / cycles
def test_consecutive_failures_tracking_and_reset_in_cycles(
    tmp_path: Path,
) -> None:
    """consecutive_failures tracks on fail cycles, resets on success or IP change."""
    db_path = tmp_path / "streak.db"
    settings = Settings(database_url=f"sqlite:///{db_path.as_posix()}")

    ping_results: dict[str, bool] = {"192.0.2.55": False}

    def _pinger(ip: str) -> bool:
        return ping_results.get(ip, False)

    app = create_app(settings, pinger=_pinger)

    with TestClient(app) as client:
        # Create camera
        cam_res = client.post(
            "/api/cameras",
            json={
                "camera_name": "Gate Cam",
                "location": "North Gate",
                "description": "Perimeter",
                "ip_address": "192.0.2.55",
            },
        )
        assert cam_res.status_code == 201
        cam_id = cam_res.json()["id"]
        assert cam_res.json()["consecutive_failures"] == 0

        engine: MonitoringEngine = app.state.monitoring_engine

        # Cycle 1: fail
        engine.run_cycle_sync()
        cam_data1 = client.get(f"/api/cameras/{cam_id}").json()
        assert cam_data1["status"] == "offline"
        assert cam_data1["consecutive_failures"] == 1

        # Cycle 2: fail
        engine.run_cycle_sync()
        cam_data2 = client.get(f"/api/cameras/{cam_id}").json()
        assert cam_data2["status"] == "offline"
        assert cam_data2["consecutive_failures"] == 2

        # Cycle 3: success -> consecutive_failures resets to 0
        ping_results["192.0.2.55"] = True
        engine.run_cycle_sync()
        cam_data3 = client.get(f"/api/cameras/{cam_id}").json()
        assert cam_data3["status"] == "online"
        assert cam_data3["consecutive_failures"] == 0

        # Cycle 4: fail again -> 1
        ping_results["192.0.2.55"] = False
        engine.run_cycle_sync()
        cam_data4 = client.get(f"/api/cameras/{cam_id}").json()
        assert cam_data4["status"] == "offline"
        assert cam_data4["consecutive_failures"] == 1

        # Change IP via PATCH -> consecutive_failures resets to 0
        patch_res = client.patch(
            f"/api/cameras/{cam_id}",
            json={"ip_address": "192.0.2.56"},
        )
        assert patch_res.status_code == 200
        patch_data = patch_res.json()
        assert patch_data["status"] == "unknown"
        assert patch_data["consecutive_failures"] == 0

