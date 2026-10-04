# Step 07: Monitoring Engine + Status API

## Overview
Step 07 implements the backend ICMP ping monitoring engine and monitoring status/control endpoints, while removing all legacy email alert machinery and schema fields.

## Key Changes
1. **Removed Alert Machinery**:
   - Dropped `alert_sent_for_current_outage` column from `cameras` via Alembic batch migration `402937679932`.
   - Purged all references to email alerting, alert thresholds, SMTP, and notification state across backend and project documentation.
   - Recorded architectural decisions in `docs/adr/0006-ping-mechanism.md` and `docs/adr/0007-no-email.md`.
2. **Monitoring State Table**:
   - Created `monitoring_state` table via Alembic migration `cc0b65b49954` with `CHECK (id = 1)` and seed row `(id=1, running=0)`.
   - Tracks `running`, `last_cycle_started_at`, and `last_cycle_finished_at`.
3. **ICMP Prober**:
   - Implemented `ping_host(ip)` in `backend/app/monitoring/probe.py` using Windows `ping -n 1 -w 1000 <ip>`.
   - Configured with `CREATE_NO_WINDOW`, a hard 3.0-second subprocess timeout, and pure byte-level classification (`exit 0`, case-insensitive `b"ttl="`, and target IP check).
4. **Monitoring Engine & Scheduler**:
   - Implemented `MonitoringEngine` in `backend/app/monitoring/engine.py`.
   - Concurrency model: Camera snapshots are probed concurrently in a `ThreadPoolExecutor` capped at 32 workers.
   - Pure I/O in worker threads: Database sessions are strictly forbidden in worker threads; all database transactions occur synchronously in the engine thread using local scoped sessions.
   - State transition rules:
     - Success: camera marked `online`, `consecutive_failures = 0`, `last_checked = now`, `last_online = now`.
     - Failure: camera marked `offline`, `consecutive_failures += 1`, `last_checked = now`, `last_online` untouched.
   - Isolation safety: camera renames preserved, IP changes discard stale results, camera deletions handled gracefully, and `updated_at` timestamps are never modified.
   - Clean shutdown & restart resumption: engine running state is persisted in SQLite. On application restart, if previously running, monitoring immediately resumes without manual intervention.
5. **Monitoring API**:
   - `GET /api/monitoring/status`: returns running state, probe interval, timestamps, and live camera summary counts (total, online, offline, unknown).
   - `POST /api/monitoring/start`: starts the scheduler and triggers an immediate cycle.
   - `POST /api/monitoring/stop`: halts future cycles, discards in-flight cycle results, and marks running as false.
   - All internal fields (`consecutive_failures`, alert fields) remain excluded from API contracts.

## Verification
- Comprehensive unit, integration, and concurrency test suites in `backend/tests/test_monitoring.py` and `backend/tests/test_probe.py`.
- Thread safety and SQLite object isolation verified across file databases.
- Full unified test suite (`python scripts/check.py`) and smoke e2e check (`python scripts/check.py --e2e`).
