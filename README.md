# Camera Monitor

Local network ICMP reachability monitor for Hikvision CCTV cameras running on an admin PC in the office server room.

## Status
- **Phase**: Step 09 - Settings (Check Interval & Theme)
- **Foundation**: FastAPI (Backend) + React 19 / Vite / Tailwind CSS v4 (Frontend) + SQLite / Alembic
- **Monitoring Engine**: Background ICMP pings run concurrently via `ThreadPoolExecutor` (max 32 workers). Probing interval configured via `MONITOR_INTERVAL_SECONDS` (default 60s, min 10s) or dynamically through the Settings interface. Engine state persists across application restarts.

## Prerequisites
- **Python**: 3.12+ (Python 3.12 recommended)
- **Node.js**: 24+ (see `.nvmrc`)
- **pnpm**: 12+
- **Git** & **GitHub CLI** (`gh`)

## Getting Started

### 1. Bootstrap Environment
Run the cross-platform setup script to create the Python virtual environment and install both backend and frontend dependencies:
```powershell
python scripts/setup.py
```

### 2. Run Quality Checks
Verify formatting, linting, type safety, and test suites across the stack:
```powershell
python scripts/check.py
```

To run Playwright end-to-end / smoke tests:
```powershell
python scripts/check.py --e2e
```

### 3. Run Development Servers
Start both backend (FastAPI at `http://localhost:8000`) and frontend (Vite at `http://localhost:5173`):
```powershell
python scripts/dev.py
```

## Documentation
- [AGENTS.md](file:///c:/Users/Richmond/Desktop/Open%20Source%20Projects/camera-ping/AGENTS.md): Architecture conventions and working agreements.
- [BUILD_PROTOCOL.md](file:///c:/Users/Richmond/Desktop/Open%20Source%20Projects/camera-ping/BUILD_PROTOCOL.md): Core planning/building protocol.
- [docs/steps/00-plan.md](file:///c:/Users/Richmond/Desktop/Open%20Source%20Projects/camera-ping/docs/steps/00-plan.md): Complete project build plan.
- [docs/adr/](file:///c:/Users/Richmond/Desktop/Open%20Source%20Projects/camera-ping/docs/adr/): Architectural Decision Records.
