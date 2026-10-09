# Operations & Maintenance Guide

This guide shows you how to manage the background service, perform backups, restore databases, monitor logs, and uninstall Camera Monitor on the server room administration PC (Windows 10 Pro 64-bit, Version 10.0.19045, 22H2).

## Understanding the Directory Structure

Camera Monitor strictly separates application code from persistent runtime data:

- **Program Directory (`C:\Program Files\CameraMonitor`)**:
  Read-only directory containing the embedded Python 3.12 64-bit runtime, FastAPI backend code, prebuilt React single-page application, and operational batch scripts.
- **Application Data Directory (`C:\ProgramData\CameraMonitor`)**:
  Read-write directory containing:
  - `camera-monitor.env`: Optional local environment configuration file.
  - `camera-monitor.lock`: Exclusive instance file lock.
  - `data\camera_monitor.db`: Primary SQLite database configured in WAL (Write-Ahead Logging) mode.
  - `logs\camera-monitor.log`: Rotating application logs (10 MB limit per file, retaining 5 rotated backups).
  - `backups\`: Rolling database snapshot archives.
  - `power-before.txt`: Original system power policy timeouts saved during installation.

## Controlling the Windows Service

Administrative management scripts are located in `C:\Program Files\CameraMonitor\scripts`.

Before running service management commands, open Command Prompt or PowerShell as Administrator and navigate to the scripts folder:
```cmd
cd "C:\Program Files\CameraMonitor\scripts"
```

### Checking Service Status

To inspect task registration, process state, memory consumption, and monitoring status:

1. Run the status script:
   ```cmd
   status.cmd
   ```
2. Review the printed diagnostics:
   - Windows Scheduled Task state (`Running` or `Ready`).
   - WorkingSet memory usage of the active Python process.
   - HTTP response status from `http://127.0.0.1:8742/api/health`.
   - Current monitoring engine state (`running` or `stopped`).

### Stopping the Service

1. Run the stop script:
   ```cmd
   stop.cmd
   ```

**Result**: Stops the `CameraMonitor` task and cleanly terminates any active backend processes.

### Starting the Service

1. Run the start script:
   ```cmd
   start.cmd
   ```

**Result**: Triggers the `CameraMonitor` task and polls the health endpoint until the server confirms readiness.

### Restarting the Service

To apply configuration changes or reset service state:

1. Run `stop.cmd`.
2. Run `start.cmd`.

**Result**: The service restarts cleanly and reloads configuration from `C:\ProgramData\CameraMonitor\camera-monitor.env`.

## Backing Up and Restoring Data

Camera Monitor provides automated daily backups and manual backup capabilities.

### Understanding Automated Backups

The Windows Scheduled Task **`CameraMonitor Backup`** (or `<TaskName> Backup`) executes `scripts\backup.cmd` every night at 03:00 under `NT AUTHORITY\SYSTEM`.

The backup process uses the SQLite Online Backup API. This API performs non-blocking, transactionally consistent snapshots while the monitoring engine actively records live camera ping events.

- **Backup destination**: `C:\ProgramData\CameraMonitor\backups\camera_monitor-YYYYMMDD-HHMMSS.db`
- **Integrity verification**: Every backup automatically executes `PRAGMA integrity_check;`.
- **Retention policy**: The script retains the 14 newest backup archives and automatically deletes older archives.

### Creating a Manual Backup

To trigger an immediate snapshot before performing system maintenance or upgrades:

1. Open an elevated command prompt in `C:\Program Files\CameraMonitor\scripts`.
2. Run the backup script:
   ```cmd
   backup.cmd
   ```

**Result**: A new timestamped database snapshot is created and verified in `C:\ProgramData\CameraMonitor\backups`.

### Restoring from a Backup

Restoring replaces the live SQLite database. Because database files cannot be replaced while in use, you must stop the service before restoring.

1. Stop the running service:
   ```cmd
   stop.cmd
   ```
2. Run the restore script, specifying the full path to your selected backup file:
   ```cmd
   restore.cmd "C:\ProgramData\CameraMonitor\backups\camera_monitor-20261006-120000.db"
   ```
   The restore script automatically:
   - Runs `PRAGMA integrity_check;` on the target backup file before applying it.
   - Archives the current database to `camera_monitor.db.before-restore`.
   - Replaces `camera_monitor.db` with the backup copy.
   - Cleans up any existing `.db-wal` or `.db-shm` temporary journal files.
3. Restart the service:
   ```cmd
   start.cmd
   ```

**Result**: The service restarts using the restored database and resumes camera monitoring.

## Monitoring Application Logs

To inspect live log events using PowerShell:

1. Open PowerShell and run:
   ```powershell
   Get-Content -Path "C:\ProgramData\CameraMonitor\logs\camera-monitor.log" -Wait -Tail 50
   ```
2. Press `Ctrl + C` when you want to stop streaming logs.

For detailed explanations of error messages and diagnostic codes, see the [Troubleshooting Guide](troubleshooting.md).

## Uninstalling Camera Monitor

You can uninstall Camera Monitor while preserving your database and ping history, or perform a complete cleanup.

### Standard Uninstallation (Preserving Inventory and Data)

To remove scheduled tasks, desktop shortcuts, and program binaries while retaining all camera records, ping history, and backups:

1. Open an elevated command prompt in `C:\Program Files\CameraMonitor\scripts`.
2. Run the uninstaller:
   ```cmd
   uninstall.cmd
   ```

**Result**: Program files and tasks are removed. All data in `C:\ProgramData\CameraMonitor` remains intact for future reinstallation.

### Complete Removal (Purging All Data)

To completely remove Camera Monitor including all databases, configuration files, and backups:

1. Open an elevated command prompt in `C:\Program Files\CameraMonitor\scripts`.
2. Run the uninstaller with the data deletion parameter:
   ```cmd
   uninstall.cmd -RemoveData DELETE
   ```

**Result**: All tasks, program files, databases, logs, and backups are permanently deleted.

### Reviewing Uninstaller Cleanup Actions

When `uninstall.cmd` executes, it performs the following steps:

1. **Stops and unregisters tasks**: Unregisters both the boot task (`CameraMonitor`) and daily backup task (`CameraMonitor Backup`).
2. **Terminates running processes**: Stops any lingering backend processes running from `C:\Program Files\CameraMonitor`.
3. **Deletes shortcut**: Removes the public `Camera Monitor` shortcut from the Windows desktop.
4. **Restores power settings**: Checks for `C:\ProgramData\CameraMonitor\power-before.txt`. If found, restores the original AC standby and hibernate timeouts using `powercfg /change standby-timeout-ac` and `powercfg /change hibernate-timeout-ac`.
5. **Removes program binaries**: Deletes `C:\Program Files\CameraMonitor` and any rollback folder `C:\Program Files\CameraMonitor.previous`.
6. **Data handling**: Deletes `C:\ProgramData\CameraMonitor` only if `-RemoveData DELETE` was explicitly passed; otherwise, preserves all data.

For daily operation procedures, see the [Operator Guide](operator-guide.md). For initial setup instructions, see the [Installation Guide](install-guide.md).
