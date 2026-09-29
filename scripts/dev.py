#!/usr/bin/env python3
"""Start backend and frontend development servers concurrently.

Ensures clean shutdown of all spawned processes and child trees on Windows and POSIX.
"""

import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import time

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"
IS_WINDOWS = platform.system() == "Windows"

VENV_DIR = BACKEND_DIR / ".venv"
VENV_BIN = VENV_DIR / "Scripts" if IS_WINDOWS else VENV_DIR / "bin"
PYTHON_BIN = VENV_BIN / ("python.exe" if IS_WINDOWS else "python")


def terminate_process_tree(proc: subprocess.Popen[bytes] | None) -> None:
    if proc is None:
        return
    try:
        if proc.poll() is None:
            pid = proc.pid
            if IS_WINDOWS:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                try:
                    os.killpg(os.getpgid(pid), signal.SIGTERM)
                except (ProcessLookupError, PermissionError):
                    proc.terminate()
            proc.wait(timeout=3)
    except Exception:
        pass


def main() -> None:
    if not PYTHON_BIN.exists():
        print(f"[ERROR] Could not find python in {PYTHON_BIN}. Please run `python scripts/setup.py` first.")
        sys.exit(1)

    pnpm_cmd = shutil.which("pnpm")
    if not pnpm_cmd:
        print("[ERROR] pnpm is not found on PATH. Please install pnpm.")
        sys.exit(1)

    backend_cmd = [str(PYTHON_BIN), "-m", "uvicorn", "app.main:app", "--reload", "--port", "8000"]
    frontend_cmd = [pnpm_cmd, "dev"]

    print("=" * 60)
    print("Camera Monitor - Development Servers")
    print("Backend:  http://localhost:8000 (API at /api/health)")
    print("Frontend: http://localhost:5173")
    print("Press Ctrl+C to stop all servers.")
    print("=" * 60)

    backend_proc: subprocess.Popen[bytes] | None = None
    frontend_proc: subprocess.Popen[bytes] | None = None
    shutting_down = False

    def shutdown(signum: int | None = None, frame: object | None = None) -> None:
        nonlocal shutting_down
        if shutting_down:
            return
        shutting_down = True
        print("\nStopping development servers...")
        terminate_process_tree(backend_proc)
        terminate_process_tree(frontend_proc)
        print("All servers stopped cleanly.")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        backend_proc = subprocess.Popen(backend_cmd, cwd=BACKEND_DIR)
        frontend_proc = subprocess.Popen(
            frontend_cmd,
            cwd=FRONTEND_DIR,
            shell=IS_WINDOWS,
        )

        while True:
            time.sleep(0.5)
            if backend_proc.poll() is not None:
                print(f"[WARNING] Backend process exited with code {backend_proc.returncode}")
                shutdown()
            if frontend_proc.poll() is not None:
                print(f"[WARNING] Frontend process exited with code {frontend_proc.returncode}")
                shutdown()
    except KeyboardInterrupt:
        shutdown()
    finally:
        shutdown()


if __name__ == "__main__":
    main()
