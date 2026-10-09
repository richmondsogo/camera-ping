# Camera Monitor Operator Quick Card

Use this quick reference card to operate Camera Monitor on the server room admin PC (Windows 10 Pro 64-bit, Version 10.0.19045).

## Accessing the Dashboard
- **Desktop shortcut**: Double-click the **Camera Monitor** shortcut on the desktop.
- **Browser URL**: Navigate to `http://127.0.0.1:8742`.

## Managing the Service
Run Command Prompt or PowerShell as Administrator in `C:\Program Files\CameraMonitor\scripts`:
- **Check status**: Run `status.cmd`.
- **Start service**: Run `start.cmd`.
- **Stop service**: Run `stop.cmd`.
- **Create backup**: Run `backup.cmd`.
- **Restore backup**: Run `stop.cmd`, then `restore.cmd "<path-to-backup.db>"`, then `start.cmd`.

## Reviewing Key Locations
- **Program files**: `C:\Program Files\CameraMonitor`
- **Configuration**: `C:\ProgramData\CameraMonitor\camera-monitor.env`
- **Active log**: `C:\ProgramData\CameraMonitor\logs\camera-monitor.log`
- **Database**: `C:\ProgramData\CameraMonitor\data\camera_monitor.db`
- **Backups**: `C:\ProgramData\CameraMonitor\backups` (created daily at 03:00; retains 14 newest copies)

## Interpreting Status Indicators
- **ONLINE (green)**: Camera responds to ICMP echo requests.
- **OFFLINE (red)**: Camera fails consecutive echo requests. Inspect physical cabling and switch power.
- **UNKNOWN (gray)**: Camera is newly added or edited; awaiting the next monitoring cycle.
- **Server unreachable**: Verify service status with `status.cmd` or inspect `camera-monitor.log`.
