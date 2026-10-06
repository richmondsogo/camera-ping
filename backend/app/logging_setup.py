from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_logging_configured = False


def is_logging_configured() -> bool:
    """Return whether root logging has been initialized via setup_logging."""
    return _logging_configured


def setup_logging(
    log_dir: Path,
    level: int = logging.INFO,
    enable_console: bool = True,
    force: bool = False,
) -> None:
    """Configure application logging with rotating file handler and console handler.

    Configures the root logger idempotently unless force=True.
    Rotating file handler: 5 MB x 5 files, UTF-8 encoded at
    <log_dir>/camera-monitor.log.
    Console handler uses errors='replace' to avoid UnicodeEncodeError on Windows.
    Disables uvicorn.access logging to avoid 5-second polling spam.
    """
    global _logging_configured
    if _logging_configured and not force:
        return

    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "camera-monitor.log"

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    handlers: list[logging.Handler] = [file_handler]

    if enable_console:
        stream = sys.stdout
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(errors="replace")
            except Exception:
                pass
        console_handler = logging.StreamHandler(stream)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(level)
        handlers.append(console_handler)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    for h in list(root_logger.handlers):
        if "LogCapture" not in h.__class__.__name__:
            root_logger.removeHandler(h)
    for h in handlers:
        root_logger.addHandler(h)

    # Disable uvicorn.access logging
    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.handlers = [logging.NullHandler()]
    uvicorn_access.propagate = False

    # Route uvicorn errors and general uvicorn logs to root logger
    logging.getLogger("uvicorn").propagate = True
    logging.getLogger("uvicorn.error").propagate = True

    _logging_configured = True
