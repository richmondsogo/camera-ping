# Camera Monitor

Camera Monitor is a local web application built for an administration PC in an office server room (Windows 10 Pro 64-bit, Version 10.0.19045, 22H2). The application monitors the reachability of local Hikvision network cameras through ICMP echo requests and displays live reachability statuses on a dashboard. Camera Monitor runs completely offline on the local network with zero external cloud dependencies.

## Key Boundaries

Camera Monitor is intentionally scoped for local server room operations:
- **No email or push notifications**: Alerts display visually on the web dashboard.
- **No remote or LAN web access**: The service binds exclusively to IPv4 loopback (`127.0.0.1:8742`) on the administration PC without remote network exposure or authentication layers.
- **ICMP reachability checks only**: An "Online" status indicates that the camera network interface responds to ICMP echo requests. It does not verify RTSP video streaming, lens status, or camera firmware health.

## Setting Up Local Development

To run Camera Monitor from source on a development machine:

1. **Bootstrap the environment**:
   ```powershell
   python scripts/setup.py
   ```
   Creates the Python virtual environment in `backend/.venv` and installs frontend dependencies via `pnpm`.

2. **Start development servers**:
   ```powershell
   python scripts/dev.py
   ```
   Starts the FastAPI backend on `http://localhost:8000` and the Vite development server on `http://localhost:5173`.

3. **Run unified quality checks**:
   ```powershell
   python scripts/check.py
   ```
   Runs backend linters, type checks, unit tests, and frontend linters, formatting checks, and test suites.

## Deploying in Production (Offline Windows PC)

To deploy Camera Monitor on an offline Windows administration PC:

1. **Build the offline distribution bundle**:
   ```powershell
   python scripts/build_bundle.py
   ```
   Generates `dist-bundle/CameraMonitor-0.9.0.zip` containing the embedded 64-bit Python runtime, application code, and prebuilt frontend assets.

2. **Transfer and extract the package**:
   Copy the archive to the administration PC and extract it to a temporary directory (for example, `C:\Temp\CameraMonitor-0.9.0`).

3. **Run the installer**:
   Open an elevated Command Prompt or PowerShell terminal in the extracted folder and run:
   ```cmd
   scripts\install.cmd
   ```

4. **Verify the service**:
   The installer registers the boot task (`CameraMonitor`) under `NT AUTHORITY\SYSTEM` (principal `S-1-5-18`), configures daily database backups at 03:00 (`CameraMonitor Backup`), disables Windows sleep timeouts, and places a desktop shortcut pointing to `http://127.0.0.1:8742`.

For detailed setup and operational instructions, see the [Installation Guide](docs/install-guide.md) and [Operations & Maintenance Guide](docs/maintenance.md).

## Exploring the Repository

- `backend/`: FastAPI application, SQLAlchemy models, Alembic migrations, and SQLite storage.
- `frontend/`: React 19 single-page application, TypeScript, Vite, Tailwind CSS v4, and component tests.
- `packaging/`: Windows deployment scripts, scheduled task definitions, and service launchers.
- `scripts/`: Development server orchestrator, bundle builder, smoke tests, and quality check suite.
- `shared/`: Shared CSV schemas, validation test vectors, and contract test fixtures.
- `docs/`: Comprehensive operator guides, installation procedures, ADRs, and configuration references.

To browse all documentation topics, see the [Documentation Index](docs/README.md).
