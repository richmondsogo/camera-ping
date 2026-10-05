# Agent Instructions & Project Conventions

## Architecture Summary
Camera Monitor is a local web application built for an admin PC in an office server room. Its purpose is to monitor the reachability of local Hikvision network cameras via ICMP ping checks and display live statuses on a clean dashboard.


The application has no external cloud runtime dependencies and operates entirely within the local office network.

```text
Admin PC (Local Network)
├── Backend (FastAPI + SQLite + Alembic + SQLAlchemy)
└── Frontend (React 19 + TypeScript + Vite + Tailwind CSS v4 + TanStack Query)
```

## Technology Stack
- **Backend**: Python 3.12+, FastAPI, SQLAlchemy, Alembic, SQLite
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS v4 (`@tailwindcss/vite`), TanStack Query
- **Testing & Quality (Backend)**: pytest, Ruff, mypy (strict)
- **Testing & Quality (Frontend)**: Vitest, Playwright, ESLint, Prettier

## Commands Reference
All standard commands are executed from the repository root using Python:

- **Setup / Bootstrap**:
  ```powershell
  python scripts/setup.py
  ```
  Creates `backend/.venv` (using `py -3.12`), installs backend dependencies, and installs frontend dependencies via `pnpm`.

- **Development Servers**:
  ```powershell
  python scripts/dev.py
  ```
  Spawns both the FastAPI backend (`http://localhost:8000`) and the Vite frontend (`http://localhost:5173`) with clean process termination on shutdown.

- **Unified Quality & Test Check**:
  ```powershell
  python scripts/check.py
  ```
  Runs backend lint (Ruff), backend typecheck (mypy strict), backend unit tests (pytest), frontend lint (ESLint), frontend formatting check (Prettier), frontend typecheck (tsc strict), and frontend unit tests (Vitest).

- **Selective Checks**:
  ```powershell
  python scripts/check.py --only-backend
  python scripts/check.py --only-frontend
  python scripts/check.py --only-lint
  python scripts/check.py --only-typecheck
  python scripts/check.py --only-tests
  python scripts/check.py --e2e   # Runs Playwright smoke/e2e tests
  # Set env var CONTRAST_REPORT=1 to print contrast tables (quiet by default unless a pair fails)
  ```

## Conventions
- **Line Endings**: LF across all files (`.gitattributes`, Prettier `endOfLine: "lf"`, Ruff `line-ending = "lf"`).
- **Type Safety**: Strict typing in both Python (mypy strict mode) and TypeScript (tsc strict mode, `noImplicitAny`).
- **Database Access**: SQLAlchemy models and queries must use absolute SQLite paths configured via `settings.database_url`. Never use cwd-relative paths. Alembic migrations must always configure `render_as_batch=True`.
- **API Boundaries**: Frontend communicates with `/api/*` through the Vite proxy in development. No CORS headers or direct host URLs hardcoded.
- **Fixtures**: All test addresses must use reserved RFC 5737 documentation blocks (`192.0.2.0/24`). Never hardcode production IP addresses.
- **Monitoring Engine**: Periodic ICMP pings run concurrently off the event loop (`ThreadPoolExecutor` max 32 workers). Probing interval is configured via `MONITOR_INTERVAL_SECONDS` (default 60s, min 10s). The engine's running state persists in SQLite (`monitoring_state`), automatically resuming on application restart if running prior to shutdown. Frontend polls cameras and monitoring status at 5000ms intervals (`POLL_INTERVAL_MS = 5000`), injectable in hooks and tests. E2E backend executes with `MONITOR_INTERVAL_SECONDS=10`.

## Working Agreement
1. **Strict Git Discipline**:
   - Create branch `step/NN-<name>` from `main`. **Never commit to `main`**.
   - Commit at each checkpoint with small, atomic commits and clear messages.
   - When done, push the branch and open a PR with `gh pr create`. PR description must include: what changed, how it was verified (paste real command output), and what is explicitly out of scope.
   - **Do NOT merge the PR. Do NOT force-push. Do NOT delete branches. Ask the user first, every time.**
2. **"Never claim done without pasting real check output"**: Every verification must be evidenced by pasting actual terminal output from the executed command.
3. **"One step per conversation, plan first, wait for approval"**: Every fresh conversation starts by reading `AGENTS.md`, drafting a numbered plan, and awaiting explicit human approval before any files are modified.
4. **"No features beyond the step's scope, name and ask instead"**: Do not speculate or implement ahead of the approved plan. If a feature or abstraction is noticed, name it and ask before building.
5. **"Secrets never in source or database, env only"**: Credentials and secrets must live strictly in environment variables, never committed to source or written into SQLite database records.
6. **"Scratch and throwaway scripts in OS temp only"**: Scratch or throwaway scripts use the OS temp directory, never `backend/data` or the repo, and are deleted afterwards.
7. **"Paste check output only from final run on final commit"**: Paste check output only from the final run on the final commit; if any file changes after a run, re-run before pasting or pushing.

