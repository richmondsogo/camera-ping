# Contributing to Camera Monitor

Thank you for your interest in improving Camera Monitor! This guide details local environment setup, architectural constraints, quality standards, and pull request guidelines.

---

## Getting Started

### Prerequisites

- **Operating System**: Windows 10 or Windows 11 64-bit (x64).
- **Python**: 3.12+ (Windows `py -3.12` launcher recommended).
- **Node.js**: Version 24+ (see `.nvmrc`).
- **pnpm**: Version 12+.
- **Git** & **GitHub CLI** (`gh`).

### Environment Bootstrap

Clone the repository and run the setup script from the root directory:

```powershell
# Bootstrap virtual environment, backend packages, and frontend dependencies
python scripts/setup.py
```

This creates `backend/.venv`, installs Python dependencies, and executes `pnpm install` in `frontend/`.

---

## Core Commands

All development tasks are coordinated through standard runner scripts:

```powershell
# 1. Start development servers (FastAPI on :8000, Vite on :5173)
python scripts/dev.py

# 2. Run single-process production runtime locally (on :8742)
pnpm --dir frontend build
python scripts/run_prod.py

# 3. Run unified quality checks (lint, format, typecheck, unit tests)
python scripts/check.py

# 4. Run Playwright end-to-end tests
python scripts/check.py --e2e

# 5. Build distribution bundle and execute standalone smoke test
python scripts/check.py --bundle
```

---

## Engineering Rules and Constraints

### 1. The Isolated E2E Stack Rule
End-to-end tests must never touch development databases (`backend/data/camera_monitor.db`) or default dev/prod ports (`8000`, `5173`, `8742`).
- Dev E2E tests run on `127.0.0.1:18000` (backend) and `localhost:15173` (Vite), using `backend/.e2e-data/e2e_cameras.db`.
- Prod E2E tests run on `http://127.0.0.1:18080`, using `backend/.e2e-data/e2e_prod_cameras.db`.
- Protected ports are guarded by assertions. Never bypass this boundary.

### 2. Design System & Design Tokens
All UI components in `frontend/` must use the design system tokens defined in `frontend/src/index.css`.
- **No ad-hoc utilities**: Do not use arbitrary classes (such as `p-[13px]`) or raw Tailwind color palettes (`text-gray-500`, `bg-blue-600`) outside token definitions.
- **Consult the specification**: See [DESIGN.md](DESIGN.md) for typography roles, spacing scales, and aesthetic non-goals.
- Validate token usage:
  ```powershell
  python scripts/lint_tokens.py
  ```

### 3. Shared Validation Vectors
Camera name and IP address validation rules must remain strictly synchronized between backend and frontend.
- Both layers validate against test cases in `shared/camera-validation-vectors.json`.
- When modifying input validation logic, update `shared/camera-validation-vectors.json` first and confirm both Python and TypeScript test suites pass.

### 4. Database Migrations
All database schema alterations use Alembic in batch mode for SQLite table constraint compatibility:
- Always ensure migration scripts specify `render_as_batch=True`.
- Refer to the [Development Guide](docs/development.md) for details on generating and testing migrations.

### 5. Line Endings & Platform Compatibility
- **LF Line Endings**: All Python, TypeScript, CSS, JSON, and Markdown files use LF line endings (`.gitattributes`, Prettier `endOfLine: "lf"`, Ruff `line-ending = "lf"`).
- **CRLF for Windows Scripts**: Windows Command scripts (`.cmd`) and PowerShell scripts (`.ps1`) require CRLF line endings.
- **PowerShell 5.1 Compatibility**: Packaging and installer scripts in `packaging/windows/` must execute reliably under Windows PowerShell 5.1 (the default built into Windows 10/11) without requiring PowerShell 7+ features.

---

## Note on Maintainer Workflow Docs

The files [AGENTS.md](AGENTS.md) and [BUILD_PROTOCOL.md](BUILD_PROTOCOL.md) document the repository maintainers' AI-assisted Planner/Builder workflow and branch disciplines. They are checked in for transparency into the project's development history and are optional reading for open-source contributors.

---

## Reporting Bugs

A good bug report helps us diagnose issues quickly without back-and-forth clarification. Please include:

1. **Host Environment**: Windows version and build (`winver` or `systeminfo`).
2. **Network Topology**: How the host PC connects to cameras (e.g., flat local subnet, routed VLAN, Wi-Fi bridge).
3. **Direct Ping Output**: Run the following in Command Prompt on the host PC and paste the output:
   ```cmd
   ping -n 1 -w 2000 <camera-ip>
   ```
4. **Log Snippets**: Relevant lines from `C:\ProgramData\CameraMonitor\logs\camera-monitor.log` (or `backend/data/logs/camera-monitor.log` in development).
5. **Observed vs. Expected Behavior**: Clear explanation of what happened versus what you expected.

---

## Submitting Pull Requests

1. Fork the repository and create a descriptive branch from `main`.
2. Make small, focused commits with clear messages.
3. Keep documentation in sync: if your change alters behavior, commands, or configuration, update the relevant files in `docs/`.
4. Ensure all quality checks pass cleanly:
   ```powershell
   python scripts/check.py
   ```
5. Open a pull request against `main`. Fill out the pull request template completely, including verification evidence.
