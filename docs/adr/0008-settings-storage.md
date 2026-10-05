# 8. Application Settings Storage and Dynamic Check Interval

Date: 2026-10-05

## Context
Camera Monitor requires configurable reachability check intervals (presets and custom duration) and display theme preferences (Light / Dark) for operators on the server room admin PC.

The check interval directly governs the background ICMP ping engine loop and must persist across application restarts. In contrast, display theme is a visual user interface preference for the local browser session.

## Decision
1. **SQLite Singleton Table (`app_settings`)**:
   - Application configuration is stored in a dedicated `app_settings` table managed via Alembic migrations with `render_as_batch=True`.
   - A single-row constraint (`CHECK (id = 1)`) and check constraint on valid intervals (`CHECK (check_interval_seconds IS NULL OR (check_interval_seconds >= 10 AND check_interval_seconds <= 31536000))`) guarantee data integrity at the database layer.
   - The table is seeded with `(1, NULL)` upon initial migration.

2. **Configuration Fallback & API Semantics**:
   - When `check_interval_seconds` is `NULL`, the application uses `MONITOR_INTERVAL_SECONDS` from the environment / `.env` (default 60 seconds).
   - `PATCH /api/settings` accepts `{ "check_interval_seconds": int }` (valid range: 10 to 31,536,000 seconds / 1 year).
   - `PATCH` cannot clear the stored value back to `NULL`. Consequently, `MONITOR_INTERVAL_SECONDS` serves strictly as the initial default until the first save, after which the database value persistently governs.

3. **Thread-Safe Engine Rescheduling**:
   - When the interval updates via API, the service notifies the monitoring engine through `engine.update_interval(new_interval)`.
   - Rescheduling utilizes sliced wait intervals (chunks up to 3600s) and a thread-safe wake method (`loop.call_soon_threadsafe(self._wake_event.set)`).
   - If a cycle is in progress, the new interval takes effect immediately upon cycle completion without extra cycles or missed wakeups.
   - If the engine is stopped, updating settings does not initiate monitoring.

4. **Client-Side Theme Persistence & Anti-Flash**:
   - Theme is stored in browser `localStorage` (`theme: 'light' | 'dark'`), defaulting to light mode.
   - An inline script in `index.html` reads `localStorage.getItem('theme')` and applies the `dark` class to `document.documentElement` before CSS and React hydrate, eliminating theme flash.

## Consequences & Costs
- Clean separation of concerns: persistent monitoring timing in SQLite, client visual preferences in `localStorage`.
- Environment variable overrides (`MONITOR_INTERVAL_SECONDS`) cease to apply once a setting has been modified and saved through the application interface.
- No network authentication or remote cloud dependencies introduced.
