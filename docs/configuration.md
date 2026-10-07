# Configuration Reference

This document describes all environment variables used across Camera Monitor backend, development scripts, and frontend test harnesses, as well as data storage paths.

## Backend Runtime Settings

These variables configure the FastAPI application. They can be set in the system environment or defined in a `.env` file at the repository root.

| Environment Variable | Default Value | Valid Range | Effect | Database Storage Counterpart |
| :--- | :--- | :--- | :--- | :--- |
| `BACKEND_HOST` | `127.0.0.1` | Valid IPv4 string | IP address interface the FastAPI backend binds to. | None |
| `BACKEND_PORT` | `8000` | `1024`–`65535` | TCP port the FastAPI backend listens on. | None |
| `DATABASE_URL` | `sqlite:///backend/data/camera_monitor.db` | SQLAlchemy SQLite URI | Connection string for SQLite database storage. Must point to an absolute path. | None |
| `MONITOR_INTERVAL_SECONDS` | `60` | `10`–`31536000` (10s to 365d) | Fallback ICMP probing interval used if no custom interval has been configured in the UI. | Stored in SQLite table `app_settings` (column `check_interval_seconds`). Dynamic DB setting takes precedence over env var. |
| `FRONTEND_DIST` | Unset (dev), `frontend/dist` (prod) | Directory path | Path to built frontend static assets. When set, activates production mode and serves the UI. | None |
| `LOG_DIR` | `backend/data/logs` | Directory path | Absolute path to directory where rotating log files are saved. | None |

## Development, Script, and Testing Variables

These variables configure developer runners, the Vite development proxy, and isolated Playwright E2E testing environments.

| Environment Variable | Default Value | Valid Range | Effect |
| :--- | :--- | :--- | :--- |
| `API_PROXY_TARGET` | `http://127.0.0.1:8000` | Valid HTTP URL | Destination backend URL that Vite proxies `/api` requests to during frontend development. |
| `PORT` | `5173` | `1024`–`65535` | Port for the Vite frontend development server. |
| `BASE_URL` | `http://localhost:15173` | Valid HTTP URL | Base URL used by Playwright test runs. |
| `CI` | Unset | Boolean flag (`true` or `1`) | Enables CI environment mode (enables HTML test reporter and headless constraints). |
| `CONTRAST_REPORT` | Unset | `0` or `1` | When set to `1`, prints full WCAG contrast calculation tables during Playwright runs. |
| `E2E_BACKEND_HOST` | `127.0.0.1` | Valid IPv4 string | Host interface used by `scripts/e2e_backend.py` for isolated test runs. |
| `E2E_BACKEND_PORT` | `18000` | `1024`–`65535` | Port used by `scripts/e2e_backend.py` to prevent conflicts with normal dev servers. |
| `E2E_FRONTEND_PORT` | `15173` | `1024`–`65535` | Port used by Vite in Playwright webServer config to isolate test browsing. |
| `E2E_PROD_PORT` | `18080` | `1024`–`65535` | Port used by the production single-process server during Playwright E2E testing. |
| `SCREENSHOTS_SUBDIR` | `step09` | String (directory name) | Subdirectory under `frontend/screenshots/` where walkthrough images are written. |
| `WALKTHROUGH` | Unset | `0` or `1` | When set to `1`, executes the opt-in 6-point screenshot walkthrough E2E test. |

## Database, Lock & File Locations

- **Active Database File**: `backend/data/camera_monitor.db` (configured via `DATABASE_URL`).
- **Instance Lock File**: `backend/data/camera-monitor.lock` (kernel byte-range lock preventing concurrent executions).
- **Log Files**: `backend/data/logs/camera-monitor.log` (rotating application log, up to 5 backups of 5 MiB each).
- **Temporary E2E Data**: `backend/.e2e-data/` (ephemeral databases and logs generated for Playwright tests, ignored by git).
- **Migration Backup Folders**: `backend/data/backup-pre-step07/` and `backend/data/backup-pre-step09/` (cold snapshots taken prior to schema migrations).

## Production Server CLI Options & Home Directory

When running the standalone server via `python -m app.serve`, the following CLI options are available:

- `--home <DIR>`: Specifies an isolated runtime root (e.g. `C:\ProgramData\CameraMonitor`). In `--home` mode:
  - Database defaults to `<DIR>/data/camera_monitor.db`.
  - Rotating logs are written to `<DIR>/logs/camera-monitor.log`. Logging initializes first, capturing all fatal startup errors (exit codes 2, 3, 4, 5).
  - An optional `<DIR>/camera-monitor.env` file is read if present. Only `BACKEND_PORT` and `MONITOR_INTERVAL_SECONDS` are allowed; real environment variables take precedence.
- `--frontend-dist <DIR>`: Path to built frontend static assets containing `index.html`.

