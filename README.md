# Camera Monitor

Camera Monitor is a local web application built for an admin PC in an office server room. Its purpose is to monitor the reachability of local Hikvision network cameras via ICMP ping checks and display live statuses on a clean dashboard. It runs completely offline on the local network with zero external cloud dependencies.

### What It Does Not Do
- **No email or push alerts**: Alerts are visual-only on the admin dashboard.
- **No external network access**: Binds exclusively to `127.0.0.1` on the admin PC with no login or LAN access.
- **ICMP ping reachability only**: "Online" indicates that the camera's network interface responds to ICMP echo requests; it does not verify RTSP video feeds, lens condition, or camera firmware state.

## Developer Quick Start

1. **Bootstrap environment** (creates backend virtualenv and installs dependencies):
   ```powershell
   python scripts/setup.py
   ```
2. **Start development servers** (FastAPI on port 8000, Vite frontend on port 5173):
   ```powershell
   python scripts/dev.py
   ```
3. **Run unified quality checks** (lint, formatting, typecheck, tests):
   ```powershell
   python scripts/check.py
   ```

## Repository Layout

- `backend/`: FastAPI backend, SQLAlchemy models, Alembic migrations, and SQLite storage.
- `frontend/`: React 19 SPA, TypeScript, Vite, Tailwind CSS v4, and Playwright tests.
- `scripts/`: Cross-platform maintenance, dev server runner, and quality verification scripts.
- `shared/`: Shared JSON test vectors and schemas used for backend/frontend contract validation.
- `docs/`: Comprehensive operator guides, architecture specifications, ADRs, and configuration references.

For complete project documentation, see the [Documentation Index](docs/README.md).
