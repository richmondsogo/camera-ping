from __future__ import annotations

import logging
import os
import platform
import socket
import sys
import time
from pathlib import Path

from app.config import BACKEND_DIR, Settings, settings
from app.logging_setup import setup_logging

logger = logging.getLogger("app.serve")
_lock_fd: int | None = None


def acquire_instance_lock(data_dir: Path) -> tuple[bool, str | None]:
    """Acquire a non-blocking exclusive file lock on camera-monitor.lock."""
    global _lock_fd
    data_dir.mkdir(parents=True, exist_ok=True)
    lock_file = data_dir / "camera-monitor.lock"

    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY

    try:
        fd = os.open(str(lock_file), flags)
    except OSError:
        return False, None

    is_win = platform.system() == "Windows"
    if is_win:
        import msvcrt

        try:
            # Ensure file is at least 101 bytes so offset 100 exists
            size = os.lseek(fd, 0, os.SEEK_END)
            if size < 101:
                os.write(fd, b" " * (101 - size))
            os.lseek(fd, 100, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        except OSError:
            # Locked by another process. Read PID from offset 0
            os.lseek(fd, 0, os.SEEK_SET)
            pid_str = os.read(fd, 16).decode("ascii", errors="ignore").strip()
            os.close(fd)
            return False, pid_str or None

        # Lock acquired: record PID at offset 0
        os.lseek(fd, 0, os.SEEK_SET)
        pid_bytes = f"{os.getpid():<16}\n".encode("ascii")
        os.write(fd, pid_bytes)
        _lock_fd = fd
        return True, None
    else:
        import fcntl

        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)  # type: ignore[attr-defined]
        except OSError:
            os.lseek(fd, 0, os.SEEK_SET)
            pid_str = os.read(fd, 16).decode("ascii", errors="ignore").strip()
            os.close(fd)
            return False, pid_str or None

        os.lseek(fd, 0, os.SEEK_SET)
        os.ftruncate(fd, 0)
        os.write(fd, f"{os.getpid()}\n".encode("ascii"))
        _lock_fd = fd
        return True, None


def create_bound_socket(
    host: str, port: int, max_retry_seconds: int = 15
) -> socket.socket:
    """Create and bind an exclusive socket on (host, port) with bounded retry."""
    start_time = time.monotonic()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    so_exclusive = getattr(socket, "SO_EXCLUSIVEADDRUSE", -5)
    sock.setsockopt(socket.SOL_SOCKET, so_exclusive, 1)

    while True:
        try:
            sock.bind((host, port))
            sock.listen(128)
            return sock
        except OSError as exc:
            err_code = getattr(exc, "winerror", None) or exc.errno
            if err_code in (10048, 48, 98):
                elapsed = time.monotonic() - start_time
                if elapsed < max_retry_seconds:
                    logger.info(
                        "Port %d in use, waiting for release (%.0fs/%ds)...",
                        port,
                        elapsed,
                        max_retry_seconds,
                    )
                    time.sleep(1.0)
                    continue
                else:
                    sock.close()
                    print(
                        f"Port {port} is already in use or reserved/blocked by Windows."
                        " Choose another port using BACKEND_PORT.",
                        file=sys.stderr,
                    )
                    sys.exit(3)
            elif err_code in (10013, 13):
                sock.close()
                print(
                    f"Port {port} is reserved or blocked by Windows. "
                    f"Choose another port using BACKEND_PORT.",
                    file=sys.stderr,
                )
                sys.exit(3)
            else:
                sock.close()
                print(
                    f"Port {port} is unavailable ({exc}). "
                    f"Choose another port using BACKEND_PORT.",
                    file=sys.stderr,
                )
                sys.exit(3)


def main() -> None:
    # 1. Configure logging
    setup_logging(log_dir=settings.log_dir)

    # 2. Validate loopback host (exit 2)
    host = os.environ.get("BACKEND_HOST", settings.backend_host)
    if host.lower() not in ("127.0.0.1", "localhost"):
        print(
            "This program only listens on this computer (127.0.0.1).", file=sys.stderr
        )
        sys.exit(2)

    # 3. Require frontend dist with index.html (exit 2)
    repo_root = BACKEND_DIR.parent
    frontend_dist_default = repo_root / "frontend" / "dist"
    frontend_dist = settings.frontend_dist or frontend_dist_default
    if not (frontend_dist.is_dir() and (frontend_dist / "index.html").is_file()):
        print("Frontend not built. Run: pnpm --dir frontend build", file=sys.stderr)
        sys.exit(2)

    # Determine data directory for lock
    if settings.database_url.startswith("sqlite:///"):
        db_path = Path(settings.database_url.replace("sqlite:///", ""))
        data_dir = db_path.parent
    else:
        data_dir = settings.log_dir.parent

    # 4. Acquire instance lock (exit 4)
    acquired, pid = acquire_instance_lock(data_dir)
    if not acquired:
        pid_msg = f" with PID {pid}" if pid else ""
        print(
            "Another instance of Camera Monitor is already running on this "
            f"data folder ({data_dir}){pid_msg}.",
            file=sys.stderr,
        )
        sys.exit(4)

    # 5. Bind port (default 8742 in prod launcher; exit 3 on failure)
    port_env = os.environ.get("BACKEND_PORT")
    port = int(port_env) if port_env else 8742

    sock = create_bound_socket(host, port)

    # 6. Run migrations (exit 5 on failure)
    app_settings = Settings(
        backend_host=host,
        backend_port=port,
        database_url=settings.database_url,
        monitor_interval_seconds=settings.monitor_interval_seconds,
        frontend_dist=frontend_dist,
        log_dir=settings.log_dir,
    )

    from alembic.config import Config

    from alembic import command

    alembic_ini_path = BACKEND_DIR / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini_path))
    alembic_cfg.attributes["skip_logging_config"] = True
    alembic_cfg.set_main_option("sqlalchemy.url", app_settings.database_url)

    try:
        command.upgrade(alembic_cfg, "head")
    except Exception as exc:
        print(
            f"Database migration failed for database file "
            f"'{app_settings.database_url}': {exc}",
            file=sys.stderr,
        )
        sock.close()
        sys.exit(5)

    # 7. Serve application
    import uvicorn

    from app.main import create_app

    app = create_app(app_settings)
    server_config = uvicorn.Config(
        app,
        log_config=None,
        loop="asyncio",
    )
    server = uvicorn.Server(server_config)

    print(
        f"Camera Monitor is running at http://127.0.0.1:{port}  (press Ctrl+C to stop)",
        flush=True,
    )

    try:
        server.run(sockets=[sock])
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
