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

## Production Deployment (Offline Windows PC)

For production deployment on an offline admin PC in the office server room:
1. Build the distribution zip: `python scripts/build_bundle.py` (or download `CameraMonitor-0.9.0.zip`).
2. Transfer the archive to the admin PC and extract to a temporary directory.
3. Right-click `scripts\install.cmd` and select **Run as administrator**.
4. The service auto-starts at boot via Windows Task Scheduler (`CameraMonitor`), creates rolling backups at 03:00, and places a desktop shortcut pointing to `http://127.0.0.1:8742`.
5. For complete details, see the [Installation Guide](docs/install-guide.md) and [Operations & Maintenance Guide](docs/maintenance.md).

## Repository Layout

- `backend/`: FastAPI backend, SQLAlchemy models, Alembic migrations, and SQLite storage.
- `frontend/`: React 19 SPA, TypeScript, Vite, Tailwind CSS v4, and Playwright tests.
- `packaging/`: Windows deployment scripts, scheduled task installers, and service lifecycle launchers.
- `scripts/`: Dev server runner, bundle builder, smoke tester, and quality verification suite.
- `shared/`: Shared CSV samples, JSON test vectors, and contract validation assets.
- `docs/`: Comprehensive operator guides, installation procedures, ADRs, and configuration references.

For complete project documentation, see the [Documentation Index](docs/README.md).
