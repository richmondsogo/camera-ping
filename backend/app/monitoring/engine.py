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
    running_since: datetime | None
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
        self._cycle_lock = threading.Lock()
        self._task: asyncio.Task[None] | None = None
        self._running_since: datetime | None = None
        self._wake_event: asyncio.Event | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

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

        with self._cycle_lock:
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

            if self._stop_event.is_set():
                return

            # 2. Probe concurrently in ThreadPoolExecutor (max 32 workers)
            workers = min(32, len(snapshot))
            probe_results: dict[int, tuple[str, bool]] = {}

            def _probe_worker(cam_id: int, ip: str) -> tuple[int, str, bool]:
                if self._stop_event.is_set():
                    return cam_id, ip, False
                try:
                    res = self.pinger(ip)
                except Exception as exc:
                    logger.warning("Pinger exception for host %s: %s", ip, exc)
                    res = False
                return cam_id, ip, res

            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [
                    executor.submit(_probe_worker, cid, ip) for cid, ip in snapshot
                ]
                for future in as_completed(futures):
                    if self._stop_event.is_set():
                        logger.info("Cycle interrupted: discarding in-flight results")
                        return
                    cid, ip, is_online = future.result()
                    probe_results[cid] = (ip, is_online)

            if self._stop_event.is_set():
                logger.info("Cycle completed after stop requested: discarding results")
                return

            # 3. Apply results in ONE transaction using DB as source of truth
            status_changes: list[str] = []
            with self.sessionmaker() as session:
                now = clock.utc_now()
                for cam_id, (probed_ip, is_online) in probe_results.items():
                    cam = session.get(Camera, cam_id)
                    if cam is None:
                        continue
                    if cam.ip_address != probed_ip:
                        # Stale result: IP changed during cycle
                        continue

                    prev_status = cam.status
                    prev_failures = cam.consecutive_failures
                    name = cam.camera_name

                    if is_online:
                        cam.status = CameraStatus.ONLINE
                        cam.consecutive_failures = 0
                        cam.last_checked = now
                        cam.last_online = now

                        if prev_status == CameraStatus.UNKNOWN:
                            status_changes.append(f"Camera '{name}' ({probed_ip}) is ONLINE")
                        elif prev_status == CameraStatus.OFFLINE:
                            suffix = "failed check" if prev_failures == 1 else "failed checks"
                            status_changes.append(
                                f"Camera '{name}' ({probed_ip}) back ONLINE after {prev_failures} {suffix}"
                            )
                    else:
                        cam.status = CameraStatus.OFFLINE
                        cam.consecutive_failures = cam.consecutive_failures + 1
                        cam.last_checked = now

                        if prev_status == CameraStatus.UNKNOWN:
                            status_changes.append(f"Camera '{name}' ({probed_ip}) is OFFLINE")
                        elif prev_status == CameraStatus.ONLINE:
                            status_changes.append(f"Camera '{name}' ({probed_ip}) went OFFLINE")

                state = session.get(MonitoringState, 1)
                if state is not None:
                    state.last_cycle_finished_at = now

                session.commit()

            for line in status_changes:
                logger.info(line)

    async def _scheduler_loop(self) -> None:
        """Periodic loop running cycles using monotonic clock intervals."""
        while not self._stop_event.is_set():
            cycle_start_mono = time.monotonic()
            try:
                await asyncio.to_thread(self.run_cycle_sync)
            except Exception:
                logger.exception("Unexpected error in monitoring cycle execution")

            cycle_elapsed = time.monotonic() - cycle_start_mono
            interval = self.interval_seconds
            if cycle_elapsed > interval:
                logger.warning(
                    "Monitoring cycle took %.2fs, exceeding configured interval of %.2fs",
                    cycle_elapsed,
                    interval,
                )

            if self._stop_event.is_set():
                break

            if self._wake_event is not None:
                self._wake_event.clear()

            while not self._stop_event.is_set():
                interval = self.interval_seconds
                elapsed = time.monotonic() - cycle_start_mono
                remaining = max(0.0, interval - elapsed)
                if remaining <= 0:
                    break
                slice_duration = min(remaining, 3600.0)

                if self._wake_event is None:
                    try:
                        await asyncio.sleep(slice_duration)
                    except asyncio.CancelledError:
                        return
                else:
                    try:
                        await asyncio.wait_for(
                            self._wake_event.wait(),
                            timeout=slice_duration,
                        )
                        self._wake_event.clear()
                    except TimeoutError:
                        pass
                    except asyncio.CancelledError:
                        return

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

            if self._running_since is None:
                self._running_since = clock.utc_now()

            if self._task is not None and not self._task.done():
                return

            self._stop_event.clear()
            self._loop = asyncio.get_running_loop()
            self._wake_event = asyncio.Event()
            self._task = asyncio.create_task(self._scheduler_loop())
            logger.info("Monitoring engine started")

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

            self._running_since = None
            self._stop_event.set()
            if self._wake_event is not None:
                self._wake_event.set()
            if self._task is not None:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
                self._task = None
            await asyncio.to_thread(self._wait_for_cycle_finish)
            logger.info("Monitoring engine stopped")

    async def shutdown(self) -> None:
        """Shutdown the running task on application exit without modifying DB flag."""
        async with self._lock:
            self._stop_event.set()
            if self._wake_event is not None:
                self._wake_event.set()
            if self._task is not None:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
                self._task = None
            await asyncio.to_thread(self._wait_for_cycle_finish)

    def wake(self) -> None:
        """Thread-safe notification to wake the sleeping scheduler if running."""
        if not self.is_running:
            return
        if self._wake_event is None or self._loop is None:
            return
        if self._loop.is_closed():
            return

        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if current_loop is self._loop:
            self._wake_event.set()
        else:
            self._loop.call_soon_threadsafe(self._wake_event.set)

    def _wait_for_cycle_finish(self) -> None:
        with self._cycle_lock:
            pass

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
            if (
                running
                and self._running_since is not None
                and started_at is not None
                and started_at >= self._running_since
            ):
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
                running_since=self._running_since if running else None,
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
