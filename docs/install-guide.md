# Camera Monitor - Windows Installation Guide

This guide details how to install and configure Camera Monitor on an offline Windows administration PC in the office server room.

## Prerequisites

- **Operating System**: Windows 10 (64-bit), Windows 11 (64-bit), or Windows Server 2016+ (64-bit).
- **Disk Space**: At least 2 GB of free space on the primary OS drive.
- **Privileges**: Local Administrator rights (required for Windows Scheduled Tasks and `Program Files` access).
- **Network**: Local office LAN access to target camera subnets. No internet access is required.

## Package Delivery

Camera Monitor is distributed as a self-contained offline archive:

```text
CameraMonitor-0.9.0.zip
├── python/        # Embedded Python 3.12 64-bit runtime and site-packages
├── app/           # Backend application code and Alembic migrations
├── frontend/dist/ # Prebuilt React 19 single-page application
├── scripts/       # Windows operations scripts and launchers
├── docs/          # Operational and administrator documentation
├── VERSION        # Release version string (0.9.0)
└── README-FIRST.txt
```

No external runtime dependencies, package managers, or compilers are needed on the target machine.

## Clean Installation Steps

1. **Transfer the Bundle**:
   Copy `CameraMonitor-0.9.0.zip` to the target machine via USB drive or trusted internal network share.

2. **Extract Archive**:
   Right-click `CameraMonitor-0.9.0.zip` and extract to a temporary folder (e.g. `C:\Temp\CameraMonitor-0.9.0`).

3. **Run the Installer**:
   Open the extracted `scripts` folder, right-click `install.cmd`, and select **Run as administrator**.
   Alternatively, run from an elevated PowerShell terminal:
   ```cmd
   scripts\install.cmd
   ```

4. **Installation Actions**:
   The installer automatically executes the following actions:
   - Verifies 64-bit Windows architecture and sufficient free disk space.
   - Copies program binaries and frontend assets to `C:\Program Files\CameraMonitor`.
   - Initializes runtime state, logs, and backups in `C:\ProgramData\CameraMonitor`.
   - Creates the default configuration file at `C:\ProgramData\CameraMonitor\camera-monitor.env` (configured for port `8742`).
   - Registers Windows Scheduled Task **`CameraMonitor`** configured to start at system boot under `NT AUTHORITY\SYSTEM` with a 30-second delay, infinite execution time limit, and automatic restart on crash.
   - Registers Windows Scheduled Task **`CameraMonitor Backup`** to run database backups daily at 03:00.
   - Configures Windows power policy to prevent the system from entering sleep/standby mode while on AC power.
   - Creates a public desktop shortcut named **Camera Monitor** pointing to `http://127.0.0.1:8742`.
   - Starts the service and verifies health endpoint response.

5. **Verify Dashboard**:
   Double-click the **Camera Monitor** desktop shortcut or open `http://127.0.0.1:8742` in your web browser.

## Upgrading an Existing Installation

To upgrade from a previous version:

1. Extract the new version archive to a temporary directory.
2. Run `scripts\install.cmd` as Administrator.
3. The installer detects the active installation, stops the running service, moves existing program binaries to `C:\Program Files\CameraMonitor.previous`, copies the new version into `C:\Program Files\CameraMonitor`, and starts the updated service.
4. All databases, historical ping logs, and configuration settings in `C:\ProgramData\CameraMonitor` are preserved.

For ongoing service management, backups, and restores, see the [Maintenance Guide](maintenance.md).
