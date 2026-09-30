# 4. Camera Data Model and API Semantics

Date: 2026-09-30

## Context
Camera Monitor requires persistent storage for monitored cameras, distinct separation between user-managed fields and ping engine monitoring state, and clean validation error messages.

## Decision
- SQLite schema enforces named constraints (`uq_cameras_ip_address`, `ck_cameras_status`, `ck_cameras_consecutive_failures`) with Alembic `render_as_batch=True`.
- `description` is required (1–500 chars), matching `camera_name` and `location` (1–100 chars).
- Updating `ip_address` resets monitoring state (`unknown` status, null timestamps, 0 failures, alert flag reset) in the same transaction. Updating other fields preserves monitoring state.
- `updated_at` advances only when user-managed field values actually change.
- Strict Pydantic models with `PydanticCustomError` eliminate "Value error, " prefixes from 422 error messages.
- App factory pattern (`create_app`) isolates database access, running Alembic migrations in lifespan with zero import-time side effects.

## Consequences & Cost
- Prevents stale outage alerts or failure counts when camera hardware/IP changes.
- Requires explicit field-change tracking in the service layer rather than automatic ORM timestamps.
- SQLite batch mode handles table recreation seamlessly during schema migrations.
