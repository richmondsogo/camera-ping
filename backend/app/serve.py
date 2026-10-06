from __future__ import annotations

import argparse
import logging
import os
import platform
import socket
import sys
import time
from pathlib import Path
from typing import Final

from app.config import BACKEND_DIR, Settings, settings
from app.logging_setup import is_logging_configured, setup_logging

logger = logging.getLogger("app.serve")
_lock_fd: int | None = None

ALLOWED_ENV_KEYS: Final[set[str]] = {"BACKEND_PORT", "MONITOR_INTERVAL_SECONDS"}


def fatal_exit(code: int, message: str, in_home_mode: bool = False) -> None:
    """Print message to stderr, write to log if active, and exit with code."""
    print(message, file=sys.stderr)
    if in_home_mode or is_logging_configured():
        logger.error("%s", message)
    sys.exit(code)


def get_app_version() -> str:
    """Read version string from VERSION file next to app package, or return 'dev'."""
    app_dir = Path(__file__).resolve().parent
    candidates = [
        app_dir / "VERSION",
        app_dir.parent / "VERSION",
        app_dir.parent.parent / "VERSION",
    ]
    for p in candidates:
        if p.is_file():
            try:
                v = p.read_text(encoding="utf-8").strip()
                if v:
                    return v
            except Exception:
                pass
    return "dev"


def load_home_env_file(home_dir: Path) -> dict[str, str]:
    """Read optional camera-monitor.env in home directory, respecting key allowlist."""
    env_file = home_dir / "camera-monitor.env"
    if not env_file.is_file():
        return {}

    loaded: dict[str, str] = {}
    try:
        content = env_file.read_text(encoding="utf-8")
    except Exception as exc:
        logger.warning("Could not read %s: %s", env_file, exc)
        return {}

    for line_no, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            logger.warning(
                "Ignoring malformed line %d in %s: %r", line_no, env_file, raw_line
            )
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip()
        if len(val) >= 2 and (
            (val.startswith('"') and val.endswith('"'))
            or (val.startswith("'") and val.endswith("'"))
        ):
            val = val[1:-1]

        if key not in ALLOWED_ENV_KEYS:
            logger.warning(
                "Ignoring unauthorized or unknown key %r on line %d in %s "
                "(allowed: %s)",
                key,
                line_no,
                env_file,
                ", ".join(sorted(ALLOWED_ENV_KEYS)),
            )
            continue
        loaded[key] = val

    return loaded


def parse_serve_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI options for Camera Monitor serve."""
    parser = argparse.ArgumentParser(description="Camera Monitor server")
    parser.add_argument(
        "--home",
        type=Path,
        default=None,
        help="Directory for runtime data, logs, and configuration",
    )
    parser.add_argument(
        "--frontend-dist",
        type=Path,
        default=None,
        help="Directory containing built frontend assets",
    )
    return parser.parse_args(argv)


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
    host: str,
    port: int,
    max_retry_seconds: int = 15,
    in_home_mode: bool = False,
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
                    msg = (
                        f"Port {port} is already in use or reserved/blocked by "
                        "Windows. Choose another port using BACKEND_PORT."
                    )
                    fatal_exit(3, msg, in_home_mode=in_home_mode)
            elif err_code in (10013, 13):
                sock.close()
                msg = (
                    f"Port {port} is reserved or blocked by Windows. "
                    "Choose another port using BACKEND_PORT."
                )
                fatal_exit(3, msg, in_home_mode=in_home_mode)
            else:
                sock.close()
                msg = (
                    f"Port {port} is unavailable ({exc}). "
                    "Choose another port using BACKEND_PORT."
                )
                fatal_exit(3, msg, in_home_mode=in_home_mode)


def main(argv: list[str] | None = None) -> None:
    args = parse_serve_args(argv)
    in_home_mode = args.home is not None
    version = get_app_version()

    if in_home_mode:
        home_dir = args.home.resolve()
        data_dir = home_dir / "data"
        log_dir = home_dir / "logs"
        data_dir.mkdir(parents=True, exist_ok=True)
        log_dir.mkdir(parents=True, exist_ok=True)
        setup_logging(log_dir=log_dir)
        file_env = load_home_env_file(home_dir)
        database_url = f"sqlite:///{(data_dir / 'camera_monitor.db').as_posix()}"
    else:
        home_dir = None
        data_dir = None
        log_dir = None
        file_env = {}
        database_url = None

    # Resolve port (real env var beats file; default 8742 in prod serve)
    if os.environ.get("BACKEND_PORT"):
        port_raw = os.environ["BACKEND_PORT"]
    elif "BACKEND_PORT" in file_env:
        port_raw = file_env["BACKEND_PORT"]
    else:
        port_raw = "8742"

    try:
        port = int(port_raw)
        if port < 1024 or port > 65535:
            raise ValueError(f"Port must be between 1024 and 65535, got {port}")
    except ValueError as exc:
        fatal_exit(2, f"Invalid BACKEND_PORT: {exc}", in_home_mode=in_home_mode)

    if in_home_mode:
        logger.info(
            "Camera Monitor %s starting, home=%s, port=%d",
            version,
            str(home_dir),
            port,
        )

    # 1. Validate loopback host (exit 2)
    # The home env file can never change the host
    host = os.environ.get("BACKEND_HOST", settings.backend_host)
    if host.lower() not in ("127.0.0.1", "localhost"):
        fatal_exit(
            2,
            "This program only listens on this computer (127.0.0.1).",
            in_home_mode=in_home_mode,
        )

    # 2. Require frontend dist with index.html (exit 2)
    if args.frontend_dist:
        frontend_dist = args.frontend_dist.resolve()
    elif os.environ.get("FRONTEND_DIST"):
        frontend_dist = Path(os.environ["FRONTEND_DIST"]).resolve()
    else:
        repo_root = BACKEND_DIR.parent
        frontend_dist_default = repo_root / "frontend" / "dist"
        frontend_dist = (settings.frontend_dist or frontend_dist_default).resolve()

    if not (frontend_dist.is_dir() and (frontend_dist / "index.html").is_file()):
        fatal_exit(
            2,
            f"Frontend not built. Run: pnpm --dir frontend build "
            f"(checked {frontend_dist})",
            in_home_mode=in_home_mode,
        )

    # If not in home mode, configure logging now and log startup
    if not in_home_mode:
        log_dir_env = os.environ.get("LOG_DIR")
        log_dir = Path(log_dir_env) if log_dir_env else settings.log_dir
        setup_logging(log_dir=log_dir)

        db_url_env = os.environ.get("DATABASE_URL")
        database_url = db_url_env if db_url_env else settings.database_url
        if database_url.startswith("sqlite:///"):
            db_path = Path(database_url.replace("sqlite:///", ""))
            data_dir = db_path.parent
        else:
            data_dir = log_dir.parent

        logger.info("Camera Monitor %s starting, home=None, port=%d", version, port)

    assert data_dir is not None
    assert log_dir is not None
    assert database_url is not None

    # Resolve monitor interval (real env var beats file)
    if os.environ.get("MONITOR_INTERVAL_SECONDS"):
        interval_raw = os.environ["MONITOR_INTERVAL_SECONDS"]
    elif "MONITOR_INTERVAL_SECONDS" in file_env:
        interval_raw = file_env["MONITOR_INTERVAL_SECONDS"]
    else:
        interval_raw = str(settings.monitor_interval_seconds)

    try:
        interval = int(interval_raw)
    except ValueError as exc:
        fatal_exit(
            2,
            f"Invalid MONITOR_INTERVAL_SECONDS: {exc}",
            in_home_mode=in_home_mode,
        )

    # 5. Acquire instance lock (exit 4)
    acquired, pid = acquire_instance_lock(data_dir)
    if not acquired:
        pid_msg = f" with PID {pid}" if pid else ""
        fatal_exit(
            4,
            "Another instance of Camera Monitor is already running on this "
            f"data folder ({data_dir}){pid_msg}.",
            in_home_mode=in_home_mode,
        )

    # 6. Bind port (exit 3)
    sock = create_bound_socket(host, port, in_home_mode=in_home_mode)

    # 7. Build Settings
    try:
        app_settings = Settings(
            backend_host=host,
            backend_port=port,
            database_url=database_url,
            monitor_interval_seconds=interval,
            frontend_dist=frontend_dist,
            log_dir=log_dir,
        )
    except Exception as exc:
        sock.close()
        fatal_exit(
            2,
            f"Configuration validation failed: {exc}",
            in_home_mode=in_home_mode,
        )

    # 8. Run migrations (exit 5 on failure)
    from alembic.config import Config

    from alembic import command

    alembic_ini_path = (BACKEND_DIR / "alembic.ini").resolve()
    alembic_cfg = Config(str(alembic_ini_path))
    alembic_cfg.attributes["skip_logging_config"] = True
    alembic_cfg.set_main_option("sqlalchemy.url", app_settings.database_url)
    alembic_cfg.set_main_option(
        "script_location", str((BACKEND_DIR / "alembic").resolve())
    )
    alembic_cfg.set_main_option("prepend_sys_path", str(BACKEND_DIR.resolve()))

    if str(BACKEND_DIR.resolve()) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR.resolve()))

    try:
        command.upgrade(alembic_cfg, "head")
    except Exception as exc:
        sock.close()
        fatal_exit(
            5,
            f"Database migration failed for database file "
            f"'{app_settings.database_url}': {exc}",
            in_home_mode=in_home_mode,
        )

    # 9. Serve application
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
