# Installation Guide

This guide shows you how to install or upgrade Camera Monitor on an offline Windows administration PC in the office server room.

## Reviewing Prerequisites

Before installing Camera Monitor, verify that your target system meets the following specifications:

- **Operating system**: Windows 10 Pro 64-bit, Version 10.0.19045 (22H2) (also supports Windows 11 64-bit and Windows Server 2016+ 64-bit).
- **Architecture**: 64-bit (x64) architecture only.
- **Disk space**: At least 2 GB of available storage on the primary OS drive (`C:`).
- **Account privileges**: Local Administrator permissions (required to register Windows Scheduled Tasks and write to `C:\Program Files`).
- **Network connectivity**: Local network Ethernet connection to target camera subnets. No internet access is required.

## Inspecting the Distribution Package

Camera Monitor is distributed as a self-contained offline ZIP archive:

```text
CameraMonitor-0.9.0.zip
├── python/        # Embedded Python 3.12 64-bit runtime and site-packages
├── app/           # Backend application code and database migrations
├── frontend/dist/ # Prebuilt React 19 single-page application
├── scripts/       # Windows operational scripts and launchers
├── docs/          # Operational and administrator documentation
├── VERSION        # Release version string (0.9.0)
└── README-FIRST.txt
```

The distribution bundle requires no external compilers, package managers, or pre-installed Python runtimes on the target PC.

## Installing Camera Monitor

Follow these steps to perform a fresh installation of Camera Monitor.

### Step 1: Transfer and Extract the Package

1. Copy `CameraMonitor-0.9.0.zip` to the target PC using a secure USB drive or local network share.
2. Right-click `CameraMonitor-0.9.0.zip`, select **Extract All…**, and choose a temporary extraction destination such as `C:\Temp\CameraMonitor-0.9.0`.

### Step 2: Run the Installer Script

1. Open the extracted folder and navigate to the `scripts` subdirectory.
2. Right-click `install.cmd` and select **Run as administrator**.

Alternatively, open an elevated Command Prompt or PowerShell terminal and run:
```cmd
cd C:\Temp\CameraMonitor-0.9.0
scripts\install.cmd
```

### Step 3: Verify Automated Installer Operations

The installer executes the following sequence automatically:

1. **System verification**: Validates 64-bit Windows architecture and checks for at least 2 GB of free disk space.
2. **Payload deployment**: Copies application binaries, embedded Python runtime, and frontend assets to `C:\Program Files\CameraMonitor`.
3. **Data initialization**: Creates the runtime data directory structure at `C:\ProgramData\CameraMonitor` for databases, logs, and backups.
4. **Configuration setup**: Generates `C:\ProgramData\CameraMonitor\camera-monitor.env` configured to bind port `8742` on `127.0.0.1`.
5. **Scheduled task registration**:
   - Registers the boot service task **`CameraMonitor`** to run under `NT AUTHORITY\SYSTEM` (principal `S-1-5-18`) with highest run level, a 30-second boot delay, infinite execution time limit (`PT0S`), `StartWhenAvailable`, `MultipleInstances=IgnoreNew`, `AllowStartIfOnBatteries`, and automatic failure restart every 1 minute (restart count 999).
   - Registers the daily maintenance task **`CameraMonitor Backup`** (or `<TaskName> Backup`) to execute database backups every day at 03:00 under `NT AUTHORITY\SYSTEM`.
6. **Power policy optimization**: Queries active AC standby and hibernate timeouts using `powercfg /query`, preserves the original settings in `C:\ProgramData\CameraMonitor\power-before.txt`, and disables standby (`standby-timeout-ac 0`) and hibernate (`hibernate-timeout-ac 0`) to prevent interruption of continuous camera monitoring. (Pass `-SkipPowerSettings` if you want to retain existing power policies).
7. **Shortcut creation**: Places a public desktop shortcut named **Camera Monitor** on the Windows desktop pointing to `http://127.0.0.1:8742`.
8. **Service verification**: Starts the background service and polls `http://127.0.0.1:8742/api/health` until the health endpoint confirms readiness.

> [!NOTE]
> The installation operates strictly within `C:\Program Files\CameraMonitor` and `C:\ProgramData\CameraMonitor`. It does not modify system `PATH`, configure firewall rules, or expose ports to external networks.

### Step 4: Confirm Dashboard Access

1. Double-click the **Camera Monitor** shortcut on the Windows desktop, or open a browser to `http://127.0.0.1:8742`.
2. Confirm that the dashboard loads and displays the monitoring interface.

**Result**: Camera Monitor is fully installed and operating as a background service.

## Upgrading an Existing Installation

To upgrade an active installation to a newer release:

### Step 1: Extract the New Release

1. Copy the new release ZIP archive to the target machine.
2. Extract the archive into a temporary folder (for example, `C:\Temp\CameraMonitor-0.9.1`).

### Step 2: Execute the Upgrade Script

1. Open an elevated Command Prompt or PowerShell terminal.
2. Run `scripts\install.cmd` from the new package directory:
   ```cmd
   cd C:\Temp\CameraMonitor-0.9.1
   scripts\install.cmd
   ```

### Step 3: Verify the Upgrade Sequence

The installer handles the upgrade seamlessly:
1. Detects the existing installation at `C:\Program Files\CameraMonitor`.
2. Stops the running `CameraMonitor` task.
3. Moves existing binaries to `C:\Program Files\CameraMonitor.previous` as a rollback fallback.
4. Copies the new runtime and code into `C:\Program Files\CameraMonitor`.
5. Preserves all camera databases, historical records, and configuration in `C:\ProgramData\CameraMonitor`.
6. Starts the updated service and verifies health endpoint response.

**Result**: The upgraded version is active while retaining your existing camera inventory and configuration.

For ongoing service management, backup procedures, and uninstallation steps, see the [Operations & Maintenance Guide](maintenance.md). For troubleshooting installation issues, see the [Troubleshooting Guide](troubleshooting.md).
