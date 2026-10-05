# Architecture

Camera Monitor is a local web application built for an offline admin PC in an office server room.

```
+-----------------------------------------------------------+
| Admin PC (127.0.0.1)                                      |
|                                                           |
|  [Vite + React Frontend] <--- HTTP /api ---> [FastAPI]   |
|         (:5173 dev)                            (:8000)    |
|                                                   |       |
|                                      +------------+---+   |
|                                      |                |   |
|                                  [SQLite]   [ThreadPool]  |
|                                  (Alembic)   (ping.exe)   |
+---------------------------------------------------|-------+
                                                    | ICMP
                                                    v
                                      [Local Network Cameras]
```

## Components

- **Frontend**: React 19 SPA with Vite, Tailwind CSS v4, and TanStack Query. Communicates with `/api/*` via proxy; polls status every 5 seconds.
- **Backend**: Python 3.12 FastAPI service with SQLAlchemy ORM, Alembic migrations, and SQLite storage.
- **Monitoring Engine**: Background thread running a periodic loop off the event loop via `ThreadPoolExecutor` (max 32 concurrent workers).

## Data Model

- `cameras`: Inventory table (`id`, `camera_name`, `ip_address`, `location`, `description`, `status`, `last_checked`, `last_online`, `consecutive_failures`).
- `monitoring_state`: Single-row table tracking engine state (`id=1`, `is_running`, `running_since`, `last_cycle_started_at`, `last_cycle_finished_at`).
- `app_settings`: Single-row key-value table for mutable configuration (`check_interval_seconds`).

## Monitoring Cycle & Online Rule

1. Engine wakes up on configured interval (or when triggered by start).
2. Reads all cameras from SQLite and records `last_cycle_started_at` in UTC.
3. Submits ICMP ping tasks concurrently to `ThreadPoolExecutor(max_workers=32)`.
4. Executes Windows OS ping: `ping.exe -n 1 -w 2000 <ip>`.
5. **Online Rule**: A camera is considered **Online** if and only if:
   - The process exit code is `0`, **AND**
   - The stdout contains `"TTL="` (case-insensitive), **AND**
   - The target IP address appears in the reply line.
   If any condition fails, the check is considered **Offline**.
6. Updates camera records (`status`, `last_checked`, `consecutive_failures`), records `last_cycle_finished_at`, and sleeps until the next scheduled cycle.

## Restart, Resume, and Time

- **Persistence**: Engine running state is persisted in `monitoring_state`. When the backend starts up, it reads `monitoring_state` and automatically resumes if it was running prior to shutdown.
- **Timestamps**: All database timestamps are stored in UTC ISO 8601 strings (`clock.now_utc()`). The frontend converts UTC timestamps to the browser's local timezone for display.

## Production Runtime Architecture

In production (`python scripts/run_prod.py`), Camera Monitor runs as a **single process** serving both the compiled React frontend and the FastAPI backend:

```text
+-----------------------------------------------------------+
| Admin PC (127.0.0.1:8742)                                 |
|                                                           |
|  [Browser] <--- HTTP ---> [Single FastAPI Process]        |
|                            ├── Plain ASGI Security Middlewares|
|                            │   ├── SecurityHeaders (outer) |
|                            │   └── HostOriginCheck (inner) |
|                            ├── API Routes (/api/*)         |
|                            ├── Static SPA Serving (dist/)  |
|                            │   ├── Fixed MIME mapping      |
|                            │   ├── Immutable assets cache  |
|                            │   └── SPA HTML fallback       |
|                            └── Monitoring Background Loop  |
|                                                           |
|                            [SQLite DB]      [Logs]        |
|                           (Instance Lock)  (Rotating)     |
+-----------------------------------------------------------+
```

### Production Mode Definition
Production mode is defined as `settings.frontend_dist` being configured (pointing to `frontend/dist`).
- In production mode, interactive API documentation routes (`/docs`, `/redoc`, `/openapi.json`) are disabled and return HTTP 404.
- In development mode (where `frontend_dist` is unset), API docs remain available at `/docs`.

### Loopback & Boundary Protection
- **Loopback Enforcement**: The production server strictly binds to `127.0.0.1` (or `localhost`) and refuses non-loopback addresses with exit code 2.
- **Host Header Validation**: ASGI middleware rejects any request whose `Host` header does not match `127.0.0.1` or `localhost` (including ports) with HTTP 400.
- **Origin Header Validation**: Mutating requests (`POST`, `PUT`, `PATCH`, `DELETE`) with an `Origin` header must originate from loopback; foreign or `null` origins are rejected with HTTP 403 without modifying state.
- **Security Headers**: Plain ASGI middleware ensures all responses (including 400, 403, 404, and unhandled 500 errors) carry `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, and `Referrer-Policy: no-referrer`.

### Static Asset Serving & MIME Mapping
- Compiled assets from `frontend/dist` are served with explicit MIME types defined in code (`.html`, `.js`, `.css`, `.woff2`, `.svg`, `.json`, etc.), completely independent of Windows registry associations.
- Assets under `/assets/*` are served with `Cache-Control: public, max-age=31536000, immutable`.
- All other paths (including `index.html`) use `Cache-Control: no-cache`.
- Extensionless paths fallback to `index.html` to support client-side routing (e.g. `/settings`). Missing files with extensions return HTTP 404.

### Instance Locking & Log Rotation
- **Single-Instance Lock**: The launcher acquires a non-blocking byte-range lock on `camera-monitor.lock` (locking byte 100 via Windows `msvcrt.LK_NBLCK` or POSIX `fcntl`) and writes its PID at offset 0. If another instance is running, it reads the PID and immediately exits with code 4.
- **Structured Log Rotation**: Logs are written to `<log_dir>/camera-monitor.log` with UTF-8 encoding using a `RotatingFileHandler` (max 5 MiB, up to 5 backups). Console logging reconfigures standard error with `errors="replace"` to prevent Windows console encoding crashes on non-ASCII characters.

## Security & File Locations

- **Security Stance**: Binds strictly to `127.0.0.1`. No external network exposure, no cloud connections, and no login system.
- **File Locations**:
  - Database: `backend/data/camera_monitor.db` (configured via `DATABASE_URL`).
  - Instance Lock: `backend/data/camera-monitor.lock`.
  - Logs: `backend/data/logs/camera-monitor.log` (configured via `LOG_DIR`).
  - Backups: `backend/data/backups/`.
