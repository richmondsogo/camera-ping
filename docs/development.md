# Development Guide

This guide covers developer environment setup, coding conventions, quality checks, and workflows.

## Prerequisites

- **Python**: 3.12+ (Windows `py -3.12` launcher recommended)
- **Node.js**: 24+ (see `.nvmrc`)
- **pnpm**: 12+
- **Git** & **GitHub CLI** (`gh`)

## Getting Started

1. **Bootstrap Virtualenv & Node Modules**:
   ```powershell
   python scripts/setup.py
   ```
2. **Start Dev Servers**:
   ```powershell
   python scripts/dev.py
   ```
   Spawns FastAPI backend (`http://localhost:8000`) and Vite frontend (`http://localhost:5173`). Press `Ctrl+C` to terminate both processes cleanly.

3. **Start Production Server Locally**:
   ```powershell
   pnpm --dir frontend build
   python scripts/run_prod.py
   ```
   Serves the compiled frontend and backend in a single process at `http://127.0.0.1:8742`.

## Development vs Production Runtime

| Dimension | Development (`scripts/dev.py`) | Production (`scripts/run_prod.py`) |
| :--- | :--- | :--- |
| **Processes** | 2 processes (FastAPI + Vite dev server) | 1 process (`app.serve` via `scripts/run_prod.py`) |
| **Frontend Serving** | Vite HMR server on port 5173 | Single-process static serving from `frontend/dist` |
| **API Proxy** | Vite reverse proxy (`/api/*` -> `:8000`) | Direct in-process route handling (`/api/*`) |
| **Ports** | Frontend `:5173`, Backend `:8000` | Single configurable loopback port (default `:8742`) |
| **API Documentation** | Enabled at `/docs` and `/redoc` | Disabled (returns HTTP 404) |
| **Security Headers** | Basic CORS proxy headers | Enforced: `nosniff`, `DENY`, `no-referrer` |
| **Logging** | Console logging | UTF-8 rotating file (`backend/data/logs/camera-monitor.log`) + console |
| **Instance Locking**| None (dev sockets) | Mandatory non-blocking file lock (`camera-monitor.lock`) |

## Unified Quality Checks

Run all static analysis and unit tests:
```powershell
python scripts/check.py
```

### Selective Flags
- `python scripts/check.py --only-backend`: Ruff lint/format, mypy strict, and pytest.
- `python scripts/check.py --only-frontend`: Token lint, ESLint, Prettier, tsc strict, Vitest, and build verification.
- `python scripts/check.py --only-lint`: Ruff, token linter, ESLint, and Prettier.
- `python scripts/check.py --only-typecheck`: mypy strict and tsc strict.
- `python scripts/check.py --only-tests`: pytest, token linter unit tests, docs checker tests, bundle builder tests, packaging script tests, and Vitest.
- `python scripts/check.py --e2e`: Runs Playwright end-to-end suite across dev and production projects.
- `python scripts/check.py --bundle`: Builds the offline distribution zip and executes the 10-step bundle smoke test.

### Opt-In Environment Variables
- `CONTRAST_REPORT=1`: Prints complete WCAG contrast measurement tables during Playwright runs.
- `WALKTHROUGH=1`: Enables the 6-point visual walkthrough screenshot test in `frontend/e2e/settings-layout-a11y.spec.ts`.
- `SCREENSHOTS_SUBDIR=<name>`: Specifies custom output subdirectory under `frontend/screenshots/`.
- `E2E_PROD_PORT=<port>`: Custom port for the production E2E test server (default `18080`).

## The Isolated E2E Stack Rule

To ensure Playwright tests never interfere with local development data or running servers:
- Dev servers run on `127.0.0.1:8000` (backend) and `localhost:5173` (frontend), using `backend/data/camera_monitor.db`.
- E2E dev tests run on `127.0.0.1:18000` (`scripts/e2e_backend.py`) and `localhost:15173` (Vite dev server), using `backend/.e2e-data/e2e_cameras.db`.
- E2E production tests run on `http://127.0.0.1:18080` (configured via `E2E_PROD_PORT`), serving compiled `frontend/dist` with `backend/.e2e-data/e2e_prod_cameras.db`.
- Running production tests alone:
  ```powershell
  pnpm --dir frontend exec playwright test --project=production
  ```
- Never run E2E tests against ports 8000, 5173, or 8742. Protected ports are guarded by `assertE2eStack`.

## Database Migrations (Windows)

All migrations use Alembic in batch mode for SQLite schema compatibility.
To generate a new migration:
```powershell
cd backend
.\.venv\Scripts\alembic revision --autogenerate -m "describe_change"
```
Always verify that generated revisions include `render_as_batch=True` on table alterations. To apply pending migrations:
```powershell
.\.venv\Scripts\alembic upgrade head
```

## Adding Design Tokens

Design tokens are centralized in `frontend/src/index.css`.
1. Add custom CSS variables under `@theme` in `frontend/src/index.css`.
2. Do not use ad-hoc inline arbitrary values (e.g. `p-[13px]`) in component files.
3. Verify compliance with the token linter:
   ```powershell
   python scripts/lint_tokens.py
   ```

## Offline Bundle & Packaging

To package and validate the offline Windows distribution:
1. **Build the Bundle**:
   ```powershell
   python scripts/build_bundle.py
   ```
   Compiles the frontend, retrieves verified embeddable Python 3.12, installs locked runtime wheels into `python/Lib/site-packages`, and produces `dist-bundle/CameraMonitor-0.9.0.zip`.
2. **Execute the Smoke Test**:
   ```powershell
   python scripts/bundle_smoke.py
   ```
   Extracts into a path with spaces, verifies isolated DLLs, tests dual-cwd execution, auto-resume, and process resilience.

## Repository Layout

- `backend/`: FastAPI application, database models, schemas, and API routers.
- `frontend/`: React components, pages, design system tokens, unit tests, and E2E specs.
- `scripts/`: Dev server launcher, setup script, unified checker, and docs validator.
- `docs/`: Architecture guides, backlog, roadmap, and ADRs.

## Pull Request Workflow

For detailed step discipline, branch naming, and review procedures, refer directly to:
- [Agent Working Agreement](../AGENTS.md)
- [Build Protocol](../BUILD_PROTOCOL.md)
