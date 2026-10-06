#!/usr/bin/env python3
"""Production launcher wrapper for Camera Monitor.

Locates backend virtualenv Python, verifies frontend build assets, sets cwd to backend/,
runs `app.serve` as a child process, forwards signals/Ctrl+C, and returns the child's exit code.
"""

import os
import platform
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"
FRONTEND_DIST = FRONTEND_DIR / "dist"

IS_WINDOWS = platform.system() == "Windows"
VENV_DIR = BACKEND_DIR / ".venv"
VENV_BIN = VENV_DIR / "Scripts" if IS_WINDOWS else VENV_DIR / "bin"
PYTHON_BIN = VENV_BIN / ("python.exe" if IS_WINDOWS else "python")


def main() -> None:
    if not PYTHON_BIN.exists():
        print(
            f"[ERROR] Could not find Python binary at {PYTHON_BIN}. Please run `python scripts/setup.py` first.",
            file=sys.stderr,
        )
        sys.exit(1)

    frontend_dist_env = os.environ.get("FRONTEND_DIST")
    frontend_dist = Path(frontend_dist_env) if frontend_dist_env else FRONTEND_DIST
    if not (frontend_dist.is_dir() and (frontend_dist / "index.html").is_file()):
        print(
            "Frontend not built. Run: pnpm --dir frontend build",
            file=sys.stderr,
        )
        sys.exit(2)

    cmd = [str(PYTHON_BIN), "-m", "app.serve", *sys.argv[1:]]

    try:
        proc = subprocess.Popen(cmd, cwd=BACKEND_DIR)
        returncode = proc.wait()
        sys.exit(returncode)
    except KeyboardInterrupt:
        try:
            returncode = proc.wait(timeout=5)
            sys.exit(returncode)
        except (subprocess.TimeoutExpired, OSError):
            sys.exit(0)


if __name__ == "__main__":
    main()
