# 9. Production Runtime Architecture

Date: 2026-10-05

## Decision
- Single process serves the API and built frontend (`FRONTEND_DIST`) on loopback only (`127.0.0.1`).
- Production mode is defined as `FRONTEND_DIST` being set; `/docs`, `/redoc`, and `/openapi.json` are disabled.
- An exclusive non-blocking file lock (`camera-monitor.lock`) guarantees a single running instance per data folder.
- Hard kill (Task Scheduler "End") is safe: OS releases the lock immediately; SQLite WAL preserves consistency.
- Host header check blocks DNS rebinding (400); Origin check blocks cross-site state mutation (403).
- Explicit extension-to-MIME mapping avoids Windows registry corruption; no CSP due to inline theme script.
- Rotating file log (`camera-monitor.log`, 5MB x 5) captures operational events without polling noise.
