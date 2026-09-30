# Step 03: Camera Model, Migration, and CRUD API

**Date:** 2026-09-30  
**Branch:** `step/03-camera-api`  
**Status:** Complete  

## Objectives
Implement the persistent database foundation, camera data model, Alembic migrations, Pydantic validation schemas, domain service layer, and thin REST API endpoints for Camera Monitor (MVP):
1. **Database Foundation & Isolation**:
   - Application factory `create_app(settings)` with zero import-time filesystem side effects.
   - Lifespan runner executing Alembic migrations to `head` on startup, with readable startup failure diagnostics naming the target database file on corrupt DB or unknown revision.
   - Per-test isolation via `tmp_path` SQLite databases migrated with real Alembic (`upgrade head`).
   - Autouse test guard ensuring production data directory (`backend/data/`) is never touched during test runs.
   - `UTCDateTime` custom SQLAlchemy `TypeDecorator` with `cache_ok = True` storing ISO 8601 strings and returning timezone-aware UTC datetimes.
   - Timezone-aware clock module (`app/clock.py`) with `clock.utc_now()` supporting test monkeypatching.
2. **Camera Model & Alembic Migration**:
   - SQLAlchemy 2.0 `Camera` model with explicit constraint naming convention.
   - Named constraints: `uq_cameras_ip_address`, `ck_cameras_status`, and `ck_cameras_consecutive_failures`.
   - Migration `e836b3b10071_create_cameras_table.py` using `render_as_batch=True`.
   - Full migration upgrade/downgrade testing and schema drift verification comparing metadata and `sqlite_master` constraint names.
3. **Pydantic Validation Schemas**:
   - `CameraCreate`, `CameraUpdate`, and `CameraRead` with strict strings and `extra="forbid"`.
   - IPv4 address canonicalization storing `str(IPv4Address)`.
   - Rejection of leading-zero octets (`192.0.002.010`), fullwidth digits (`１９２.０.２.１０`), `0.0.0.0`, multicast (`224.0.0.0/4`), and broadcast (`255.255.255.255`).
   - Rejection of control characters (ASCII < 32 and 127, including newlines and tabs) across all text fields.
   - Required `description` (1–500 chars), `camera_name` and `location` (1–100 chars).
   - Use of `PydanticCustomError` to eliminate "Value error, " prefix from 422 error details.
   - `CameraUpdate` distinguishes omitted fields from explicit `null` (422) and rejects empty update bodies `{}` (422).
4. **Service Layer & Domain Logic**:
   - Pure domain exceptions (`CameraNotFoundError`, `DuplicateIpError`) mapped to HTTP 404 and 409 in centralized FastAPI exception handlers.
   - Changing `ip_address` resets camera monitoring state (`unknown` status, null timestamps, 0 consecutive failures, alert sent flag cleared) in the same database transaction.
   - Editing other fields (`camera_name`, `location`, `description`) preserves active monitoring state.
   - `updated_at` advances only when user-managed field values actually change.
5. **REST API Endpoints (`/api/cameras`)**:
   - `POST /api/cameras`: 201 Created with initial `unknown` status and clean defaults.
   - `GET /api/cameras`: 200 OK with camera list ordered by `id` ASC.
   - `GET /api/cameras/{id}`: 200 OK or 404 Not Found.
   - `PATCH /api/cameras/{id}`: 200 OK or 404/409/422.
   - `DELETE /api/cameras/{id}`: 204 No Content or 404 Not Found.
   - Internal monitoring fields (`consecutive_failures`, `alert_sent_for_current_outage`) are strictly absent from all response models.

---

## Checkpoint Summary
- [x] **Checkpoint 1 (Housekeeping & Build Verification Script)**: Created roadmap (`docs/roadmap.md`), updated backlog (`docs/backlog.md`), enhanced `frontend/scripts/verify-css-utilities.mjs` with non-vacuous guard, CSS selector checks, and styleguide tree-shaking verification. Wired into `scripts/check.py`.
- [x] **Checkpoint 2 (Database Foundation)**: `app/clock.py`, `app/database.py`, `app/main.py` (`create_app`), `backend/alembic/env.py`, `backend/tests/conftest.py` with autouse guard and per-test `tmp_path` fixtures.
- [x] **Checkpoint 3 (Model & Migration)**: `Camera` model, migration `e836b3b10071_create_cameras_table.py`, upgrade/downgrade test, schema drift test, and raw constraint verification.
- [x] **Checkpoint 4 (Pydantic Schemas)**: `CameraCreate`, `CameraUpdate`, `CameraRead` in `app/schemas/camera.py` with comprehensive schema tests.
- [x] **Checkpoint 5 (Service Layer & API)**: `app/exceptions.py`, `app/services/cameras.py`, `app/api/cameras.py`, app startup error handling tests (`test_startup.py`).
- [x] **Checkpoint 6 (API and Integration Tests)**: `backend/tests/test_cameras_api.py` covering full CRUD lifecycle, IP/text validation, partial updates, state reset, timestamp behavior, 404s, 409s, and persistence across restarts.
- [x] **Checkpoint 7 (Documentation & Verification)**: ADR 0004, step summary, full test verification, dev runner smoke test, cwd independence test, git cleanliness check.
