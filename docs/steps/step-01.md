# Step 01: Project Scaffold

**Date:** 2026-09-29  
**Branch:** `step/01-scaffold`  
**Status:** Complete  

## Objectives
Establish the foundation and project scaffolding for Camera Monitor with strictly no application features, models, or screens:
1. Repo docs skeleton (`AGENTS.md`, `DESIGN.md`, `README.md`, `BUILD_PROTOCOL.md`, ADRs, step log).
2. Backend scaffold (`backend/`: Python 3.12+, FastAPI, SQLAlchemy Base, Alembic initialized, SQLite via config, pytest, Ruff, mypy strict, `GET /api/health`).
3. Frontend scaffold (`frontend/`: React 19, TypeScript, Vite, Tailwind CSS v4, TanStack Query, Vitest, Playwright smoke test, placeholder page).
4. Standard root commands (`python scripts/check.py`, `python scripts/dev.py`, `python scripts/setup.py`).
5. Dev fixtures (`backend/app/dev_fixtures.py` with RFC 5737 addresses).
6. Config (`.gitignore`, `.env.example`, `.gitattributes`, `.nvmrc`).
7. CI (GitHub Actions workflow running `check.py` on `windows-latest`).

## Checkpoint Progress
- [x] Checkpoint 1: Repo docs skeleton and ADRs (`42530a0`)
- [x] Checkpoint 2: Backend scaffold (`41fe784`)
- [x] Checkpoint 3: Frontend scaffold (`48db728`)
- [x] Checkpoint 4: Standard commands and scripts (`1d80079`)
- [x] Checkpoint 5: Dev fixtures (`7db4865`)
- [x] Checkpoint 6: Configuration files (`c878fba`)
- [x] Checkpoint 7: Continuous Integration workflow (`d9997a7`)

---

## What Actually Happened & Technical Details

### Checkpoint 1: Repo Docs Skeleton
- Created `.gitattributes` enforcing `* text=auto eol=lf` across all platforms to prevent line ending mismatches between Windows and CI.
- Created `.nvmrc` pinning Node.js LTS version 24.
- Created `AGENTS.md` containing the architecture summary, technology stack overview, standard commands, code conventions, and the mandatory Working Agreement.
- Kept `BUILD_PROTOCOL.md` intact at repo root.
- Created `DESIGN.md` placeholder documenting that design tokens and component primitives will be established in Step 02.
- Updated `README.md` with project description, prerequisites, and instructions on running setup, checks, and dev servers.
- Authored `docs/adr/0001-stack.md` (16 lines, under the 25-line limit) recording the architectural stack decision.
- Authored `docs/adr/0002-git-workflow.md` (17 lines) recording the branch-per-step and PR workflow.
- Initialized `docs/steps/step-01.md`.

### Checkpoint 2: Backend Scaffold
- Initialized `backend/` with `pyproject.toml` specifying Python 3.12+ compatibility, strict mypy configuration, Ruff linting rule set (`E`, `F`, `I`, `UP`, `B`) with `line-ending = "lf"`, and pytest.
- Configured `backend/app/config.py` using `pydantic-settings` to dynamically compute an absolute default SQLite database URL (`sqlite:///.../backend/data/camera_monitor.db`), preventing accidental relative-path databases when started from different working directories.
- Configured `backend/app/database.py` with an empty declarative `Base` (zero models) and SQLite `connect_args={"check_same_thread": False}`.
- Initialized Alembic (`alembic/env.py`) reading `settings.database_url`, targeting `Base.metadata`, and enabling `render_as_batch=True` for SQLite batch operations.
- Implemented single endpoint `GET /api/health` returning `{"status": "ok"}` with zero CORS middleware (handled via Vite proxy).
- Added passing unit test in `backend/tests/test_health.py` using `fastapi.testclient.TestClient`.

### Checkpoint 3: Frontend Scaffold
- Initialized `frontend/` using React 19, TypeScript (strict mode enabled with `noImplicitAny` and null checks), Vite 6, and Tailwind CSS v4 via `@tailwindcss/vite` (no `tailwind.config.js` or `postcss.config.js`).
- Pinned `packageManager` to `pnpm@12.4.1` and configured `allowBuilds: esbuild: true` in `pnpm-workspace.yaml`.
- Configured Vite development server at port 5173 with proxy forwarding `/api` to backend `http://127.0.0.1:8000`.
- Integrated TanStack Query (`@tanstack/react-query`) with placeholder page `frontend/src/App.tsx` querying `/api/health`.
- Configured ESLint flat config (`eslint.config.js`), Prettier (`.prettierrc` and `.prettierignore`), Vitest (excluding `e2e/**`), and Playwright.
- Implemented Vitest unit test in `frontend/src/App.test.tsx` and Playwright smoke test in `frontend/e2e/smoke.spec.ts`.

### Checkpoint 4: Standard Commands
- Created cross-platform `scripts/setup.py` to bootstrap a clean checkout: creates `backend/.venv` using `py -3.12`, installs backend dependencies with dev tools, installs frontend dependencies, and approves pnpm builds.
- Created `scripts/check.py` which detects the operating system, locates virtual environment binaries, and sequentially runs backend Ruff lint, Ruff format check, mypy strict, pytest, frontend ESLint, Prettier format check, TypeScript strict typecheck, and Vitest. Supports flags `--only-backend`, `--only-frontend`, `--only-lint`, `--only-typecheck`, `--only-tests`, and `--e2e`.
- Created `scripts/dev.py` which concurrently spawns both FastAPI and Vite servers. On Windows, it handles child process termination using `taskkill /F /T /PID` to prevent orphaned `uvicorn --reload` worker processes upon Ctrl+C.

### Checkpoint 5: Dev Fixtures
- Created `backend/app/dev_fixtures.py` defining reserved test IP constants (`192.0.2.10`, `192.0.2.11`, `192.0.2.12`) with explicit RFC 5737 documentation range comments and zero ping code.
- Created `backend/tests/test_fixtures.py` verifying via Python's `ipaddress` module that all test fixture addresses reside strictly inside `192.0.2.0/24`.

### Checkpoint 6: Configuration
- Updated `.gitignore` to comprehensively ignore:
  - Frontend: `node_modules/`, `frontend/dist/`, `playwright-report/`, `test-results/`, `*.tsbuildinfo`, `.vite/`
  - Backend: `backend/data/`, `*.db`, `*.db-wal`, `*.db-shm`, `*.sqlite3*`, `.venv/`, `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`
  - Secrets: `.env`, `.env.*`, preserving `!.env.example`
  - OS files: `Thumbs.db`, `.DS_Store`, `desktop.ini`
- Created `.env.example` with non-secret placeholders (`BACKEND_HOST`, `BACKEND_PORT`, `DATABASE_URL`) matching `config.py` and noting that real secrets live in the runtime environment only.

### Checkpoint 7: Continuous Integration
- Created `.github/workflows/ci.yml` running on `windows-latest`.
- Configured to trigger on pull requests to `main` and pushes to `main`.
- Runs `python scripts/setup.py` and `python scripts/check.py`.

---

## Real Command Verification Output

### 1. Unified Quality Checks (`python scripts/check.py`)
```text
============================================================
Camera Monitor - Quality Checks
Platform: Windows (11)
============================================================

---> [Backend: Ruff Lint]
     CMD: C:\Users\Richmond\Desktop\Open Source Projects\camera-ping\backend\.venv\Scripts\ruff.exe check .
     PASS (0.05s)

---> [Backend: Ruff Format Check]
     CMD: C:\Users\Richmond\Desktop\Open Source Projects\camera-ping\backend\.venv\Scripts\ruff.exe format --check .
     PASS (0.05s)

---> [Backend: mypy (Strict)]
     CMD: C:\Users\Richmond\Desktop\Open Source Projects\camera-ping\backend\.venv\Scripts\mypy.exe .
     PASS (1.10s)

---> [Backend: pytest]
     CMD: C:\Users\Richmond\Desktop\Open Source Projects\camera-ping\backend\.venv\Scripts\pytest.exe
     PASS (2.13s)

---> [Frontend: ESLint]
     CMD: C:\Users\Richmond\AppData\Roaming\npm\pnpm.CMD run lint
     PASS (3.45s)

---> [Frontend: Prettier Format Check]
     CMD: C:\Users\Richmond\AppData\Roaming\npm\pnpm.CMD run format:check
     PASS (1.35s)

---> [Frontend: tsc (Strict)]
     CMD: C:\Users\Richmond\AppData\Roaming\npm\pnpm.CMD exec tsc -b
     PASS (4.42s)

---> [Frontend: Vitest]
     CMD: C:\Users\Richmond\AppData\Roaming\npm\pnpm.CMD run test
     PASS (7.77s)

============================================================
[PASSED] All checks passed successfully in 20.31s!
============================================================
```

### 2. Playwright Smoke Test (`python scripts/check.py --e2e`)
```text
============================================================
Camera Monitor - Quality Checks
Platform: Windows (11)
============================================================

---> [E2E: Playwright Smoke Test]
     CMD: C:\Users\Richmond\AppData\Roaming\npm\pnpm.CMD run test:e2e
$ playwright test
[WebServer] INFO:     Started server process [2104]
[WebServer] INFO:     Waiting for application startup.
[WebServer] INFO:     Application startup complete.
[WebServer] INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
[WebServer] $ vite

Running 1 test using 1 worker

  ok 1 [chromium] › e2e\smoke.spec.ts:3:1 › smoke test: loads page and verifies health check (2.4s)

  1 passed (9.5s)
     PASS (11.35s)

============================================================
[PASSED] All checks passed successfully in 11.35s!
============================================================
```

### 3. Dev Server & Clean Shutdown Verification (`python scripts/dev.py`)
```text
=== STARTING DEV.PY ===
$ vite
INFO: Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO: Started reloader process [12320] using WatchFiles
  VITE v6.4.3 ready in 1045 ms
  ➜ Local: http://localhost:5173/
INFO: Started server process [23724]
INFO: Application startup complete.

=== VERIFYING ENDPOINTS ===
Backend Health: {"status":"ok"}
Frontend HTTP Status: 200

=== STOPPING DEV PROCESS TREE ===
(taskkill /F /T kills entire tree including reloader process and uvicorn child process)

=== PROCESSES AFTER SHUTDOWN (EXPECT ZERO PYTHON) ===
(empty output: 0 python processes running)
```

---

## Out of Scope Confirmation
The following items were explicitly out of scope for Step 01 and have **not** been built or stubbed:
- Camera database model / schema
- Any CRUD operations (add, edit, delete, list cameras)
- ICMP ping execution and monitoring scheduler engine
- Microsoft email alerts / OAuth / SMTP delivery
- CSV import / export
- Settings page and configuration persistence
- Design tokens and component styling (deferred to Step 02)
- App shell and navigation
- Libraries deferred to subsequent steps: `shadcn`, `TanStack Table`, `React Hook Form`, `Zod`
