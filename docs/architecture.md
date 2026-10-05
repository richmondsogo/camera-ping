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

## Security & File Locations

- **Security Stance**: Binds strictly to `127.0.0.1`. No external network exposure, no cloud connections, and no login system.
- **File Locations**:
  - Database: `backend/data/camera_monitor.db` (configured via `DATABASE_URL`).
  - Backups: `backend/data/backups/`.
