#!/usr/bin/env python3
"""Bootstrap environment for Camera Monitor.

Creates backend virtual environment with Python 3.12+, installs backend
dependencies with dev tools, and installs frontend dependencies with pnpm.
"""

from pathlib import Path
import platform
import shutil
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"
VENV_DIR = BACKEND_DIR / ".venv"


def run_command(cmd: list[str], cwd: Path, description: str) -> None:
    print(f"\n==> {description}...")
    print(f"    Running: {' '.join(cmd)} (in {cwd.name}/)")
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        print(f"\n[ERROR] Command failed with exit code {result.returncode}: {' '.join(cmd)}")
        sys.exit(result.returncode)


def get_python_launcher() -> list[str]:
    """Find Python 3.12+ executable for virtual environment creation."""
    is_windows = platform.system() == "Windows"
    if is_windows:
        # Check if py launcher has 3.12
        try:
            res = subprocess.run(["py", "-3.12", "-V"], capture_output=True, text=True)
            if res.returncode == 0:
                return ["py", "-3.12"]
        except FileNotFoundError:
            pass

    # Fallback to sys.executable if it meets version requirements
    if sys.version_info >= (3, 12):
        return [sys.executable]

    print("[ERROR] Python 3.12+ is required. Please install Python 3.12.")
    sys.exit(1)


def main() -> None:
    print("=" * 60)
    print("Camera Monitor Setup & Bootstrap")
    print("=" * 60)

    # 1. Create backend virtual environment if not present
    if not VENV_DIR.exists():
        py_launcher = get_python_launcher()
        run_command(py_launcher + ["-m", "venv", str(VENV_DIR)], BACKEND_DIR, "Creating backend virtualenv")
    else:
        print(f"Backend virtual environment already exists at {VENV_DIR.relative_to(REPO_ROOT)}")

    # 2. Locate pip in venv
    is_windows = platform.system() == "Windows"
    pip_bin = VENV_DIR / "Scripts" / "pip.exe" if is_windows else VENV_DIR / "bin" / "pip"

    if not pip_bin.exists():
        print(f"[ERROR] Could not find pip in {pip_bin}")
        sys.exit(1)

    # 3. Install backend dependencies
    run_command([str(pip_bin), "install", "-e", ".[dev]"], BACKEND_DIR, "Installing backend dependencies")

    # 4. Verify pnpm exists
    pnpm_cmd = shutil.which("pnpm")
    if not pnpm_cmd:
        print("[ERROR] pnpm is not found on PATH. Please install pnpm (>=12).")
        sys.exit(1)

    # 5. Install frontend dependencies
    run_command(["pnpm", "install"], FRONTEND_DIR, "Installing frontend dependencies")

    # 6. Approve pnpm build scripts if required by pnpm 12
    run_command(["pnpm", "approve-builds", "--all"], FRONTEND_DIR, "Approving pnpm lifecycle builds")

    print("\n" + "=" * 60)
    print("[SUCCESS] Setup complete! You can now run:")
    print("  python scripts/check.py  # Run all static analysis & tests")
    print("  python scripts/dev.py    # Start dev servers")
    print("=" * 60)


if __name__ == "__main__":
    main()
