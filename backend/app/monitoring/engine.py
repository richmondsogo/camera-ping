import asyncio
import logging
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app import clock
from app.models.camera import Camera, CameraStatus
from app.models.monitoring import MonitoringState
from app.monitoring.probe import ping_host

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MonitoringStatus:
    running: bool
    interval_seconds: int
    last_cycle_started_at: datetime | None
    last_cycle_finished_at: datetime | None
    next_check_at: datetime | None
    total: int
    online: int
    offline: int
    unknown: int


class MonitoringEngine:
    """Core background monitoring engine.

    Coordinates concurrent ICMP probes off the event loop, atomically applies
    system-managed status updates to SQLite, schedules periodic cycles via
    monotonic clocks, and survives application restarts.
    """

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        pinger: Callable[[str], bool] = ping_host,
        interval: float | Callable[[], float] = 60.0,
    ) -> None:
        self.sessionmaker = session_factory
        self.pinger = pinger
        self._interval = interval
        self._lock = asyncio.Lock()
        self._stop_event = threading.Event()
        self._task: asyncio.Task[None] | None = None

    @property
    def interval_seconds(self) -> float:
        if callable(self._interval):
            return float(self._interval())
        return float(self._interval)

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    def run_cycle_sync(self) -> None:
        """Execute a single monitoring cycle synchronously.

        Snapshots cameras, executes pings concurrently in a ThreadPoolExecutor
        (pure I/O, no DB sessions in threads), and atomically updates camera
        states in a single transaction if not stopped.
        """
        if self._stop_event.is_set():
            return

        cycle_started_at = clock.utc_now()

        # 1. Snapshot all cameras and update last_cycle_started_at
        with self.sessionmaker() as session:
            state = session.get(MonitoringState, 1)
            if state is not None:
                state.last_cycle_started_at = cycle_started_at
                session.commit()

            stmt = select(Camera.id, Camera.ip_address).order_by(Camera.id.asc())
            snapshot = [(row[0], row[1]) for row in session.execute(stmt).all()]

        if not snapshot:
            with self.sessionmaker() as session:
                state = session.get(MonitoringState, 1)
                if state is not None:
                    state.last_cycle_finished_at = clock.utc_now()
                    session.commit()
            return

        # 2. Probe concurrently in ThreadPoolExecutor (max 32 workers)
        workers = min(32, len(snapshot))
        probe_results: dict[int, tuple[str, bool]] = {}

        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_cam = {
                executor.submit(self.pinger, ip): (cam_id, ip)
                for cam_id, ip in snapshot
            }
            for future in as_completed(future_to_cam):
                cam_id, ip = future_to_cam[future]
                if self._stop_event.is_set():
                    logger.info("Cycle interrupted: discarding in-flight results")
                    return
                try:
                    is_online = future.result()
                except Exception as exc:
                    logger.warning("Pinger exception for host %s: %s", ip, exc)
                    is_online = False
                probe_results[cam_id] = (ip, is_online)

        if self._stop_event.is_set():
            logger.info("Cycle completed after stop requested: discarding results")
            return

        # 3. Apply results in ONE transaction using DB as source of truth
        with self.sessionmaker() as session:
            now = clock.utc_now()
            for cam_id, (probed_ip, is_online) in probe_results.items():
                cam = session.get(Camera, cam_id)
                if cam is None:
                    continue
                if cam.ip_address != probed_ip:
                    # Stale result: IP changed during cycle
                    continue

                if is_online:
                    cam.status = CameraStatus.ONLINE
                    cam.consecutive_failures = 0
                    cam.last_checked = now
                    cam.last_online = now
                else:
                    cam.status = CameraStatus.OFFLINE
                    cam.consecutive_failures = cam.consecutive_failures + 1
                    cam.last_checked = now

            state = session.get(MonitoringState, 1)
            if state is not None:
                state.last_cycle_finished_at = now

            session.commit()

    async def _scheduler_loop(self) -> None:
        """Periodic loop running cycles using monotonic clock intervals."""
        while not self._stop_event.is_set():
            cycle_start_mono = time.monotonic()
            try:
                await asyncio.to_thread(self.run_cycle_sync)
            except Exception:
                logger.exception("Unexpected error in monitoring cycle execution")

            if self._stop_event.is_set():
                break

            interval = self.interval_seconds
            elapsed = time.monotonic() - cycle_start_mono
            sleep_duration = max(0.0, interval - elapsed)

            try:
                await asyncio.sleep(sleep_duration)
            except asyncio.CancelledError:
                break

    async def start(self) -> None:
        """Start the monitoring scheduler and immediately execute the first cycle.

        Persists running=true to monitoring_state. Idempotent.
        """
        async with self._lock:
            with self.sessionmaker() as session:
                state = session.get(MonitoringState, 1)
                if state is not None:
                    state.running = True
                    session.commit()

            if self._task is not None and not self._task.done():
                return

            self._stop_event.clear()
            self._task = asyncio.create_task(self._scheduler_loop())

    async def stop(self) -> None:
        """Stop future monitoring cycles and discard in-flight cycle results.

        Persists running=false to monitoring_state. Idempotent.
        """
        async with self._lock:
            with self.sessionmaker() as session:
                state = session.get(MonitoringState, 1)
                if state is not None:
                    state.running = False
                    session.commit()

            self._stop_event.set()
            if self._task is not None:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
                self._task = None

    async def shutdown(self) -> None:
        """Shutdown the running task on application exit without modifying DB flag."""
        async with self._lock:
            self._stop_event.set()
            if self._task is not None:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
                self._task = None

    def get_status(self, db: Session | None = None) -> MonitoringStatus:
        """Retrieve current monitoring state and camera counts."""
        session_to_use = db if db is not None else self.sessionmaker()
        close_needed = db is None

        try:
            state = session_to_use.get(MonitoringState, 1)
            running = state.running if state is not None else False
            started_at = state.last_cycle_started_at if state is not None else None
            finished_at = state.last_cycle_finished_at if state is not None else None

            interval_int = int(round(self.interval_seconds))
            next_check_at: datetime | None = None
            if running and started_at is not None:
                next_check_at = started_at + timedelta(seconds=interval_int)

            total = session_to_use.scalar(select(func.count(Camera.id))) or 0
            online = (
                session_to_use.scalar(
                    select(func.count(Camera.id)).where(
                        Camera.status == CameraStatus.ONLINE
                    )
                )
                or 0
            )
            offline = (
                session_to_use.scalar(
                    select(func.count(Camera.id)).where(
                        Camera.status == CameraStatus.OFFLINE
                    )
                )
                or 0
            )
            unknown = (
                session_to_use.scalar(
                    select(func.count(Camera.id)).where(
                        Camera.status == CameraStatus.UNKNOWN
                    )
                )
                or 0
            )

            return MonitoringStatus(
                running=running,
                interval_seconds=interval_int,
                last_cycle_started_at=started_at,
                last_cycle_finished_at=finished_at,
                next_check_at=next_check_at,
                total=total,
                online=online,
                offline=offline,
                unknown=unknown,
            )
        finally:
            if close_needed:
                session_to_use.close()
