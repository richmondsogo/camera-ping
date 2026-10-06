# Camera Monitor - Server Room Operator Quick Card

## Access
- **Dashboard URL**: `http://127.0.0.1:8742`
- **Desktop Shortcut**: Double-click **Camera Monitor** on the Windows Desktop.

## Service Commands (Run as Administrator)
Open Command Prompt in `C:\Program Files\CameraMonitor\scripts`:
- **Check Status**: `status.cmd`
- **Start Service**: `start.cmd`
- **Stop Service**: `stop.cmd`
- **Manual Backup**: `backup.cmd`
- **Restore Backup**: `stop.cmd` then `restore.cmd "<path-to-backup.db>"` then `start.cmd`

## File Locations
- **Program Files**: `C:\Program Files\CameraMonitor`
- **Configuration**: `C:\ProgramData\CameraMonitor\camera-monitor.env`
- **Logs**: `C:\ProgramData\CameraMonitor\logs\camera-monitor.log`
- **Database**: `C:\ProgramData\CameraMonitor\data\camera_monitor.db`
- **Backups**: `C:\ProgramData\CameraMonitor\backups` (automatic daily at 03:00, 14 kept)

## Common Status Indicators
- **Green Pill (ONLINE)**: Camera responded to ICMP ping.
- **Red Pill (OFFLINE)**: Camera failed consecutive ping checks.
- **Gray Pill (UNKNOWN)**: Camera newly added; awaiting first ping cycle.
- **Service Offline**: Run `status.cmd` or inspect `logs\camera-monitor.log`.
