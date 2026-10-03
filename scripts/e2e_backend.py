#!/usr/bin/env python3
"""Launcher for isolated E2E backend server.

Runs uvicorn in-process against a wiped, dedicated SQLite database in backend/.e2e-data/.
"""

import os
import platform
import socket
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
E2E_DATA_DIR = BACKEND_DIR / ".e2e-data"
IS_WINDOWS = platform.system() == "Windows"
VENV_DIR = BACKEND_DIR / ".venv"
VENV_BIN = VENV_DIR / "Scripts" if IS_WINDOWS else VENV_DIR / "bin"
PYTHON_BIN = VENV_BIN / ("python.exe" if IS_WINDOWS else "python")


def ensure_venv_python() -> None:
    """Ensure the script runs with the backend venv Python interpreter."""
    if PYTHON_BIN.exists() and Path(sys.executable).resolve() != PYTHON_BIN.resolve():
        os.execv(str(PYTHON_BIN), [str(PYTHON_BIN), *sys.argv])


def is_port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def wipe_e2e_data() -> None:
    E2E_DATA_DIR.mkdir(parents=True, exist_ok=True)
    for p in E2E_DATA_DIR.glob("*"):
        if p.is_file() and (
            p.suffix in {".db", ".sqlite3"} or "-wal" in p.name or "-shm" in p.name
        ):
            try:
                p.unlink()
            except OSError as err:
                print(
                    f"[ERROR] Failed to wipe e2e database file {p}: {err}",
                    file=sys.stderr,
                )
                sys.exit(1)


def main() -> None:
    ensure_venv_python()

    port = int(os.environ.get("E2E_BACKEND_PORT", "18000"))
    host = os.environ.get("E2E_BACKEND_HOST", "127.0.0.1")

    if is_port_in_use(host, port):
        print(
            f"[ERROR] Port {port} is already in use. E2E backend server cannot start.",
            file=sys.stderr,
        )
        sys.exit(1)

    wipe_e2e_data()

    db_path = E2E_DATA_DIR / "e2e_cameras.db"
    db_url = f"sqlite:///{db_path.resolve().as_posix()}"
    os.environ["DATABASE_URL"] = db_url
    os.environ["BACKEND_PORT"] = str(port)
    os.environ["BACKEND_HOST"] = host

    sys.path.insert(0, str(BACKEND_DIR))
    import uvicorn
    from app.config import Settings
    from app.main import create_app

    app_settings = Settings(database_url=db_url, backend_port=port, backend_host=host)
    app = create_app(app_settings)

    print(f"[E2E Backend] Running on http://{host}:{port} with database {db_url}")
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
