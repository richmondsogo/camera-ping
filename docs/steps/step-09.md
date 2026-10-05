# Step 09: Settings — Check Interval & Theme

**Date:** 2026-10-05  
**Branch:** `step/09-settings`  
**Status:** Complete  

## Overview
Step 09 introduces the application Settings interface, allowing administrators to configure reachability check intervals (presets + custom amount & unit) and toggle between Light and Dark display themes.

The check interval dynamically and safely reschedules the running background ICMP monitoring engine, persisting in a new SQLite singleton table (`app_settings`), while display theme persists in browser `localStorage` with zero-flash rendering.

---

## Key Changes

### 1. Backend & Database
- **SQLite Singleton Table (`app_settings`)**:
  - Alembic migration `a4297e38199c_create_app_settings_table.py` creates table with `CHECK (id = 1)` and `CHECK (check_interval_seconds IS NULL OR (check_interval_seconds >= 10 AND check_interval_seconds <= 31536000))`.
  - Initial seed row inserted: `(1, NULL)`.
  - SQLAlchemy model `AppSettings` in `backend/app/models/setting.py`.
- **API Endpoints (`/api/settings`)**:
  - `GET /api/settings`: returns `check_interval_seconds` (stored) and `effective_check_interval_seconds` (falling back to `MONITOR_INTERVAL_SECONDS` if null).
  - `PATCH /api/settings`: updates `check_interval_seconds` (10 to 31,536,000s) and triggers dynamic engine interval update. As documented in ADR 0008, PATCH cannot clear the stored value.
- **Dynamic Thread-Safe Engine Rescheduling**:
  - `MonitoringEngine.update_interval(new_interval)` updates the loop timing.
  - Sliced sleep in chunks up to 3600s ensures long intervals wake promptly when cancelled or rescheduled.
  - `wake()` uses `loop.call_soon_threadsafe(self._wake_event.set)` to safely wake the scheduler from any thread.
  - Interval updates during an active ping cycle take effect after the cycle ends without extra cycles or missed wakeups.

### 2. Frontend Data Layer & Helpers
- **API Client & Zod Schemas**:
  - Added `getSettings()` and `updateSettings()` to `frontend/src/lib/api.ts`.
  - Added `settingsResponseSchema` and `settingsUpdateSchema` to `frontend/src/lib/schemas.ts`.
- **Interval Helpers (`frontend/src/features/settings/utils.ts`)**:
  - `toSeconds(amount, unit)` and `secondsToCustom(seconds)` convert between units (seconds, minutes, hours, days, weeks, months).
  - `parseAmount(input)` sanitizes text input, stripping leading zeros and enforcing positive integers.
  - `validateInterval(amount, unit)` enforces the 10s to 31,536,000s range.
  - `formatInterval(seconds)` produces friendly display strings (`"60 seconds"`, `"5 minutes"`, `"2 hours"`).
  - `formatClockTime(isoString, now)` formats next/last check times (`"14:32:05"`, `"Tomorrow at 14:32"`, `"Oct 12 at 14:32"`).

### 3. Theme Management & Anti-Flash
- **Theme Provider (`frontend/src/lib/theme.tsx`)**:
  - Supports `'light'` and `'dark'` modes, persisting to `localStorage.getItem('theme')`.
  - Synchronizes the `.dark` class on `document.documentElement`.
- **Anti-Flash Implementation (`frontend/index.html`)**:
  - Added inline blocking script in `<head>` to read `localStorage` and set `html.dark` before CSS or React loads.

### 4. Settings UI & Monitoring Panel
- **Settings Page (`frontend/src/pages/SettingsPage.tsx`)**:
  - Monitoring Section: Preset dropdown (`30 seconds`, `1 minute`, `5 minutes`, `15 minutes`, `1 hour`, `Custom…`).
  - Custom interval row with plain text numeric input and unit select. Prefills from `secondsToCustom` without marking form dirty until user edits.
  - Long interval warning (> 1 hour) in amber callout.
  - Save button with dirty tracking, loading state, inline error recovery (`role="alert"`), and success feedback ("Saved.").
  - Appearance Section: Theme dropdown (`Light`, `Dark`).
- **Monitoring Panel (`frontend/src/features/monitoring/MonitoringPanel.tsx`)**:
  - Updated to display "Checks every <formatted>" and calendar-aware next check timing.

---

## Verification Table

| Test Suite / Inspection | Verification Details | Tool Used | Result |
| :--- | :--- | :--- | :--- |
| **Backend Lint** | Ruff format & lint checks across backend codebase | `ruff check backend` | Pass (0 errors) |
| **Backend Typecheck** | Mypy strict mode type analysis | `mypy --strict backend` | Pass (0 errors) |
| **Backend Unit & Migration Tests** | 205 pytest tests (settings API, engine rescheduling, thread safety, migration) | `pytest backend/tests` | Pass (205 passed) |
| **Frontend Lint** | ESLint check across all TSX/TS source files | `eslint frontend` | Pass (0 warnings) |
| **Frontend Formatting** | Prettier check across frontend code | `prettier --check frontend` | Pass (all formatted) |
| **Frontend Typecheck** | TypeScript strict compilation check | `tsc --noEmit` (pnpm) | Pass (0 errors) |
| **Frontend Unit Tests** | 100 Vitest component & helper unit tests | `vitest run` (pnpm) | Pass (100 passed) |
| **E2E Integration Tests** | 20 Playwright tests across settings, cameras, and monitoring | `playwright test` | Pass (20 passed) |
| **Visual Walkthrough & Contrast** | Settings page walkthrough, light/dark themes, responsive viewports | `playwright test e2e/walkthrough.spec.ts` | Pass (6 screenshots) |

---

## Screenshot Artifacts
Visual verification walkthrough produced the following screenshots in `frontend/screenshots/step09/`:
1. `01-settings-default-light.png`: Default Settings page in light mode.
2. `02-settings-custom-dirty.png`: Custom interval configuration (2 hours) with amber warning and active Save button.
3. `03-settings-saved-notice.png`: Successful save with green "Saved." confirmation.
4. `04-settings-dark-mode.png`: Dark mode Settings page.
5. `05-dashboard-dark-mode.png`: Dark mode Dashboard with 30 cameras and updated interval display ("Checks every 2 hours").
6. `06-settings-custom-error.png`: Validation error feedback on out-of-range custom input.

---

## Out of Scope (Explicitly Deferred)
- System theme detection (`prefers-color-scheme`).
- Email alerts or notifications (dropped; admin PC is offline).
- User authentication or multi-tenant user settings.
- Modifying camera table or CSV schema.
- Automatic reset button for clearing stored settings back to default.
