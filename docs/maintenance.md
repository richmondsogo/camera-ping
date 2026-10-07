# Camera Monitor - Operations & Maintenance Guide

This document describes routine maintenance, service management, backup/restore procedures, and uninstallation for Camera Monitor on Windows.

## Directory Structure

In production, the application splits code and runtime data across two dedicated locations:

- **Program Files (`C:\Program Files\CameraMonitor`)**:
  Read-only executable payload containing embedded Python, backend application code, prebuilt React frontend assets, and operational scripts.
- **Application Data (`C:\ProgramData\CameraMonitor`)**:
  Read-write directory containing:
  - `camera-monitor.env`: Optional local environment configuration file.
  - `camera-monitor.lock`: Exclusive instance file lock.
  - `data\camera_monitor.db`: Primary SQLite database in WAL mode.
  - `logs\camera-monitor.log`: Rotating application logs (10 MB per file, 5 rotated backups).
  - `backups\`: Rolling database snapshot archives.

## Service Control

Administrative operations scripts are located in `C:\Program Files\CameraMonitor\scripts`.

### Checking Service Status

To inspect task health, running process IDs, memory usage, and monitoring engine status:

```cmd
cd "C:\Program Files\CameraMonitor\scripts"
status.cmd
```

The script prints the Windows Scheduled Task state, process WorkingSet memory, `/api/health` response, and current monitoring engine state.

### Stopping the Service

```cmd
cd "C:\Program Files\CameraMonitor\scripts"
stop.cmd
```

Stops the `CameraMonitor` task and terminates any lingering backend processes.

### Starting the Service

```cmd
cd "C:\Program Files\CameraMonitor\scripts"
start.cmd
```

Starts the `CameraMonitor` task and polls `http://127.0.0.1:8742/api/health` until the service responds.

## Backup & Restore

### Automated Backups

The Windows Scheduled Task **`CameraMonitor Backup`** executes `scripts\backup.cmd` every night at 03:00.
The backup procedure uses the SQLite Online Backup API, enabling non-blocking, transactionally consistent backups while the live monitoring engine is actively writing ping records.

Backups are saved to:
`C:\ProgramData\CameraMonitor\backups\camera_monitor-YYYYMMDD-HHMMSS.db`

Each backup automatically runs a `PRAGMA integrity_check;`. The backup script retains the newest 14 backups and prunes older archives.

### Manual Backup

To trigger an immediate backup:

```cmd
cd "C:\Program Files\CameraMonitor\scripts"
backup.cmd
```

### Restoring from a Backup

Restoring replaces the active SQLite database and requires stopping the service first:

1. Stop the running service:
   ```cmd
   stop.cmd
   ```

2. Execute the restore script, specifying the full path to the desired backup:
   ```cmd
   restore.cmd "C:\ProgramData\CameraMonitor\backups\camera_monitor-20261006-120000.db"
   ```

   The script verifies database integrity before applying changes, archives the existing database to `camera_monitor.db.before-restore`, replaces `camera_monitor.db`, and purges any stale `.db-wal` or `.db-shm` files.

3. Restart the service:
   ```cmd
   start.cmd
   ```

## Log Monitoring & Troubleshooting

Logs are written to `C:\ProgramData\CameraMonitor\logs\camera-monitor.log`.
To view real-time log activity using PowerShell:

```powershell
Get-Content -Path "C:\ProgramData\CameraMonitor\logs\camera-monitor.log" -Wait -Tail 50
```

For error codes and resolution steps, consult the [Troubleshooting Guide](troubleshooting.md).

## Uninstallation

### Standard Uninstallation (Preserving Data)

To remove scheduled tasks, desktop shortcuts, and program files while preserving all camera records, ping history, configuration, and database backups:

```cmd
cd "C:\Program Files\CameraMonitor\scripts"
uninstall.cmd
```

### Complete Removal (Including Data)

To perform a complete removal including all data, configuration, and logs:

```cmd
uninstall.cmd -RemoveData DELETE
```

### What Uninstallation Reverts

When `uninstall.cmd` runs, it executes the following cleanup sequence:

1. **Scheduled Tasks**: Stops and unregisters both the `CameraMonitor` boot task and the `CameraMonitor Backup` task.
2. **Processes**: Terminates any active backend processes originating from `C:\Program Files\CameraMonitor`.
3. **Desktop Shortcut**: Deletes the public `Camera Monitor.lnk` shortcut from the common desktop.
4. **Power Settings**: Checks for `C:\ProgramData\CameraMonitor\power-before.txt`:
   - If present, restores the original AC standby and hibernate timeouts via `powercfg /change standby-timeout-ac <min>` and `powercfg /change hibernate-timeout-ac <min>`, printing the restored values.
   - If `-SkipPowerSettings` was used at install time or the file is missing, it prints a note and leaves the existing Windows power policy unchanged.
5. **Program Binaries**: Completely deletes `C:\Program Files\CameraMonitor` and any `C:\Program Files\CameraMonitor.previous` backup directory.
6. **Data Retention**: Preserves `C:\ProgramData\CameraMonitor` (database, ping logs, and backups) unless `-RemoveData DELETE` is specified.

> [!NOTE]
> Like the installer, uninstallation is strictly self-contained. It leaves system PATH, firewall rules, and external Windows components untouched.
