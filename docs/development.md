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
- `python scripts/check.py --only-tests`: pytest, token linter unit tests, and Vitest.
- `python scripts/check.py --e2e`: Runs Playwright end-to-end and smoke test suite.

### Opt-In Environment Variables
- `CONTRAST_REPORT=1`: Prints complete WCAG contrast measurement tables during Playwright runs.
- `WALKTHROUGH=1`: Enables the 6-point visual walkthrough screenshot test in `frontend/e2e/settings-layout-a11y.spec.ts`.
- `SCREENSHOTS_SUBDIR=<name>`: Specifies custom output subdirectory under `frontend/screenshots/`.

## The Isolated E2E Stack Rule

To ensure Playwright tests never interfere with local development data or running servers:
- Dev servers run on `127.0.0.1:8000` (backend) and `localhost:5173` (frontend), using `backend/data/camera_monitor.db`.
- E2E tests run on `127.0.0.1:18000` (`scripts/e2e_backend.py`) and `localhost:15173` (Vite dev server), using an ephemeral database in `backend/.e2e-data/`.
- Never run E2E tests against ports 8000 or 5173.

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

## Repository Layout

- `backend/`: FastAPI application, database models, schemas, and API routers.
- `frontend/`: React components, pages, design system tokens, unit tests, and E2E specs.
- `scripts/`: Dev server launcher, setup script, unified checker, and docs validator.
- `docs/`: Architecture guides, backlog, roadmap, and ADRs.

## Pull Request Workflow

For detailed step discipline, branch naming, and review procedures, refer directly to:
- [Agent Working Agreement](../AGENTS.md)
- [Build Protocol](../BUILD_PROTOCOL.md)
