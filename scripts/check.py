#!/usr/bin/env python3
"""Unified quality check script for Camera Monitor.

Executes linters, format checkers, strict typecheckers, and unit tests across
backend and frontend with cross-platform OS handling.
"""

import argparse
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"
IS_WINDOWS = platform.system() == "Windows"

VENV_DIR = BACKEND_DIR / ".venv"
VENV_BIN = VENV_DIR / "Scripts" if IS_WINDOWS else VENV_DIR / "bin"


def get_backend_binary(name: str) -> Path:
    suffix = ".exe" if IS_WINDOWS else ""
    binary = VENV_BIN / f"{name}{suffix}"
    if not binary.exists():
        print(f"[ERROR] Could not find {name} in {binary}.")
        print("Please run `python scripts/setup.py` first.")
        sys.exit(1)
    return binary


def get_pnpm_cmd() -> str:
    pnpm = shutil.which("pnpm")
    if not pnpm:
        print("[ERROR] pnpm is not found on PATH. Please install pnpm.")
        sys.exit(1)
    return pnpm


class CheckRunner:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.pnpm = get_pnpm_cmd()
        self.ruff = str(get_backend_binary("ruff"))
        self.mypy = str(get_backend_binary("mypy"))
        self.pytest = str(get_backend_binary("pytest"))

    def run_step(self, name: str, cmd: list[str], cwd: Path) -> bool:
        print(f"\n---> [{name}]")
        print(f"     CMD: {' '.join(cmd)}")
        start = time.time()
        result = subprocess.run(cmd, cwd=cwd)
        elapsed = time.time() - start
        if result.returncode == 0:
            print(f"     PASS ({elapsed:.2f}s)")
            return True
        else:
            print(f"     FAIL ({elapsed:.2f}s) - Exit code: {result.returncode}")
            self.failures.append(name)
            return False

    def run_backend_lint(self) -> None:
        self.run_step("Backend: Ruff Lint", [self.ruff, "check", "."], BACKEND_DIR)
        self.run_step("Backend: Ruff Format Check", [self.ruff, "format", "--check", "."], BACKEND_DIR)

    def run_backend_typecheck(self) -> None:
        self.run_step("Backend: mypy (Strict)", [self.mypy, "."], BACKEND_DIR)

    def run_backend_tests(self) -> None:
        self.run_step("Backend: pytest", [self.pytest], BACKEND_DIR)

    def run_frontend_lint(self) -> None:
        self.run_step("Frontend: ESLint", [self.pnpm, "run", "lint"], FRONTEND_DIR)
        self.run_step("Frontend: Prettier Format Check", [self.pnpm, "run", "format:check"], FRONTEND_DIR)

    def run_frontend_typecheck(self) -> None:
        self.run_step("Frontend: tsc (Strict)", [self.pnpm, "exec", "tsc", "-b"], FRONTEND_DIR)

    def run_frontend_tests(self) -> None:
        self.run_step("Frontend: Vitest", [self.pnpm, "run", "test"], FRONTEND_DIR)

    def run_e2e_tests(self) -> None:
        self.run_step("E2E: Playwright Smoke Test", [self.pnpm, "run", "test:e2e"], FRONTEND_DIR)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run quality checks for Camera Monitor")
    parser.add_argument("--only-backend", action="store_true", help="Run only backend checks")
    parser.add_argument("--only-frontend", action="store_true", help="Run only frontend checks")
    parser.add_argument("--only-lint", action="store_true", help="Run only linters and format checkers")
    parser.add_argument("--only-typecheck", action="store_true", help="Run only typecheckers")
    parser.add_argument("--only-tests", action="store_true", help="Run only unit tests")
    parser.add_argument("--e2e", action="store_true", help="Run Playwright end-to-end / smoke tests")

    args = parser.parse_args()
    runner = CheckRunner()

    print("=" * 60)
    print("Camera Monitor - Quality Checks")
    print(f"Platform: {platform.system()} ({platform.release()})")
    print("=" * 60)

    start_total = time.time()

    if args.e2e:
        runner.run_e2e_tests()
    elif args.only_backend:
        runner.run_backend_lint()
        runner.run_backend_typecheck()
        runner.run_backend_tests()
    elif args.only_frontend:
        runner.run_frontend_lint()
        runner.run_frontend_typecheck()
        runner.run_frontend_tests()
    elif args.only_lint:
        runner.run_backend_lint()
        runner.run_frontend_lint()
    elif args.only_typecheck:
        runner.run_backend_typecheck()
        runner.run_frontend_typecheck()
    elif args.only_tests:
        runner.run_backend_tests()
        runner.run_frontend_tests()
    else:
        # Default suite: all linters, typecheckers, and unit tests
        runner.run_backend_lint()
        runner.run_backend_typecheck()
        runner.run_backend_tests()
        runner.run_frontend_lint()
        runner.run_frontend_typecheck()
        runner.run_frontend_tests()

    total_time = time.time() - start_total
    print("\n" + "=" * 60)
    if runner.failures:
        print(f"[FAILED] {len(runner.failures)} check(s) failed in {total_time:.2f}s:")
        for fail in runner.failures:
            print(f"  - {fail}")
        print("=" * 60)
        sys.exit(1)
    else:
        print(f"[PASSED] All checks passed successfully in {total_time:.2f}s!")
        print("=" * 60)
        sys.exit(0)


if __name__ == "__main__":
    main()
