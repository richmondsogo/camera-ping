# Notes for later steps

## For Step 06 (ping discovery) and Step 07 (monitoring engine)

- Sequential pings do not scale. One check can take up to ~2s, so 30 unreachable cameras take up to ~60s, which equals the whole default check interval. The engine must ping concurrently.
- On Windows, ping.exe can exit with code 0 when a router replies "Destination host unreachable". Exit code alone is not proof of reachability. Step 06 must test this on the real Windows machine and decide whether to also require "TTL=" in the output, and verify that works on non-English Windows.
- The legacy v1 script kept its state in memory only. The new design persists failure streaks in the database so restarts do not lose them. The restart test (failure #7, restart, failure #8) proves this.

## CSV-first import (Step 05)

- The owner says most cameras will be added by CSV import and manual entry is the exception.
- Required headers are exactly: `camera_name,location,description,ip_address`.
- Accept the file only if everything matches the contract, otherwise reject the whole file and commit nothing (no partial imports).
- Open decisions to raise at that step:
  - A preview-and-confirm step before committing imported rows to the database.
  - How row-level errors are reported and displayed in the UI.

## Ports and network binding (Steps 08 and 13)

- The admin PC runs other software, so the app's port must not be assumed free.
- Owner decision: Access is admin PC only: bind 127.0.0.1, no LAN access, no login.
- Requirements:
  - One configurable port from environment variable.
  - An uncommon default port (not 8000 or 5173).
  - Default bind to `127.0.0.1` (admin PC only, since there is no authentication).
  - If the port is taken, fail at startup with a clear message naming the port and the env var to change.
  - In production, the backend serves the built frontend on that single port.
  - `dev.py`, the Vite proxy target, and the Playwright `webServer` config must read the ports from env vars instead of hardcoding them.
- Note: Do not change any code for this in Step 03.

## Housekeeping notes

- Starlette's `httpx` deprecation warning in pytest (`StarletteDeprecationWarning: Using 'httpx' with 'starlette.testclient' is deprecated; install 'httpx2' instead.`) — revisit if it becomes an error.
- `contrast.spec.ts` is ~900 lines; consider splitting it if it grows further.
- The "Dialog: Overlay backdrop" contrast pair has a 1:1 threshold and can never fail (remove it or give it a real threshold).

## Known gaps after Step 04 & 05

- Location is free text with no normalization (case variants show as separate locations).
- IP validation rules exist in two places (backend and frontend). While cross-checked against `shared/camera-validation-vectors.json`, frontend trimming (`String.prototype.trim()`) is stricter than Python `strip()` on certain non-ASCII whitespace characters (e.g. U+0085).
- No sorting or pagination in camera table (deferred per design, displaying API order).
- No polling until Step 08 (user must reload or perform actions to see updated status).
- Exported CSV is not directly re-importable without removing the last three columns (`status`, `last_checked`, `last_online`), as import strictly enforces the 4-column contract (`camera_name,location,description,ip_address`).
- Formula injection risk on CSV export: fields beginning with `= + - @` are exported unescaped; if opened in Microsoft Excel, formulas could trigger warnings or execute if untrusted user input is exported.

## Known gaps after Step 07 & 08

- No recovered/outage history (deferred).
- Live browser tab title with offline count implemented in Step 08 (`(N offline) Camera Monitor`).
- Future alert enhancement idea: optional audible alert (Web Audio API or audio beep) when a camera transitions from online to offline while dashboard is open.
- If every camera fails in one cycle the admin PC's own network is the likely cause (all-offline banner added in Step 08).

## For Step 13 (deploy)

- The admin PC will reboot. The app must auto-start (Task Scheduler or a service wrapper) and resume monitoring state.
- Add a Host-header check to the backend (reject unexpected Host values) as a hardening measure against browser-based requests to localhost.

### Offline deployment (Step 13)

- The admin PC has no internet, so install needs a prebuilt frontend (`pnpm build` on the dev PC), a pre-downloaded wheel folder (`pip download`), an offline Python installer, and auto-start; no network calls at runtime.

### Office acceptance (Step 13 / 15)

- Unplug one camera and verify Offline after a cycle.
- Ping an unused camera-subnet address and a router-unreachable address, compare real ping.exe outputs, and replace the synthetic fixtures in `backend/tests/fixtures/ping` with real captures.

## Offline bundle (Step 14)

The admin PC has no internet at any time. Plan: one folder or zip containing the 64-bit Python 3.12 embeddable runtime (same minor version as development), runtime dependencies pre-installed from pinned versions on the dev PC, backend code, prebuilt frontend, install/start/stop/uninstall scripts, a scheduled task that starts the app at boot and restarts it on failure, a VERSION file, the operator documentation, and a fresh empty database (no test cameras). Nothing is downloaded at install time.

## Questions for the office visit

- `winver` / `systeminfo` output (Windows version, 64-bit?)
- Whether the Windows account has administrator rights
- Whether Python is already installed on the admin PC
- Whether the PC is set to sleep or hibernate
- Whether the cameras are on the same subnet or another VLAN

## Decided against / deferred

- Sorting offline cameras first (rows would jump under the cursor every 5 seconds)
- Audible alert (decide after the office test; browsers block sound until the page has been clicked once)
- `httpx2` test-client deprecation (dev-only, not installed)
- Click the offline count to filter (possible small addition)


