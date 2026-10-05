# Operator Guide

This guide explains how to use Camera Monitor to track office CCTV camera availability.

## The Dashboard

The dashboard provides a live overview of camera reachability across the office network.

### Camera Statuses
- **Online**: The camera is reachable and replied to ICMP echo requests.
- **Offline**: The camera failed to respond. When offline, a badge indicates failure duration: `(1 check)` or `(N checks)`.
- **Unknown**: The camera has been added or edited and has not yet been probed in an active monitoring cycle.

### Monitoring Controls & Panel Fields
- **Start**: Begins automated reachability checks in the background. State changes to `Monitoring running` with a green indicator.
- **Stop**: Pauses reachability checks. State changes to `Monitoring stopped` with a gray indicator.
- **Summary Counts**: Shows total cameras and how many are currently `online`, `offline`, or `unknown`.
- **Last check**: Displays when the previous probing cycle completed (e.g. `Last check 10:45 AM`).
- **Next check**: Displays when the next cycle is scheduled to start (e.g. `Next check in 45s`).
- **Checks every**: Current configured probing interval (e.g. `Checks every 1 minute`).

### Banners and Notices
- **Stopped Notice**:
  `Monitoring is stopped. Statuses below are from the last check.`
  *Action*: Press the **Start** button if reachability checks should resume.
- **Connection Lost Banner**:
  `Can't reach the server. Showing data from <time>. Retrying…`
  *Action*: The dashboard cannot communicate with the local backend service. The dashboard will automatically retry. Check that the backend process is running.
- **Stalled Banner**:
  `Monitoring looks stalled: no completed check since <time>.`
  *Action*: Monitoring is marked running, but no check cycle has finished recently. Check server workload or restart the monitor.
- **All Offline Banner**:
  `Every camera is offline. If that's unexpected, check this PC's network connection.`
  *Action*: Check whether the admin PC's network cable is disconnected or the local network switch is down.

## Managing Cameras

### Adding a Camera
Click **Add Camera**. Enter the camera name, optional location, optional description, and a valid IPv4 address. Click **Add Camera** to save. New cameras appear in `Unknown` status until the next cycle.

### Editing a Camera
Click **Edit** next to any camera row.
> **Note**: Changing the IP address displays the warning: `Changing the IP address resets this camera's reachability statistics and monitoring history.` The status resets to `Unknown` and failure counts clear.

### Deleting a Camera
Click **Delete** next to a camera row. A confirmation dialog will prompt: `Are you sure you want to delete camera "<Name>" (<IP>)? This action cannot be undone.` Click **Delete Camera** to confirm.

## CSV Import & Export

### Importing Cameras via CSV
1. Click **Import CSV** in the toolbar.
2. Ensure your CSV file has the exact 4 header columns:
   `camera_name,location,description,ip_address`
3. If creating the file in Microsoft Excel, select **Save As** and choose **CSV UTF-8 (Comma delimited) (*.csv)**.
4. Select your file in the dialog. The system performs dry-run validation automatically.
5. If errors are found, an error table shows **Line**, **Column**, and the specific **Problem**. **Nothing is imported if any row is wrong.** Correct the file and re-upload.
6. Once valid, review the row preview and click **Import Cameras** to commit.

### Exporting Cameras
Click **Export CSV** to download the current camera list. The export includes all inventory fields plus current status and timestamps.

## Settings

Navigate to **Settings** in the header navigation:
- **Check Interval**: Select a preset (`10 seconds`, `30 seconds`, `1 minute`, `2 minutes`, `5 minutes`, `10 minutes`) or choose `Custom…` to specify any duration between 10 seconds and 365 days.
- **Long Interval Warning**: Selecting an interval of 1 hour or greater displays: `Outages may take up to <duration> to detect.`
- **Appearance**: Toggle between `Light` and `Dark` theme.

## Running in Production

### Starting the Application
From the repository root on the admin PC, start the application with:
```powershell
python scripts/run_prod.py
```

When ready, the server prints:
```text
Camera Monitor is running at http://127.0.0.1:8742  (press Ctrl+C to stop)
```

Open a web browser on the admin PC and navigate to:
```text
http://127.0.0.1:8742
```
> **Note**: Always use `http://127.0.0.1:8742`. (If `localhost` behaves differently on your network setup, verify at the office; `127.0.0.1` is guaranteed to bind strictly to loopback).

### Stopping the Application
To shut down Camera Monitor cleanly, return to the terminal running the launcher and press `Ctrl+C`. The server will stop background monitoring threads, release the instance lock, and terminate.

### Common Startup Messages & Solutions
- **Port already in use or reserved**:
  `Port 8742 is already in use or reserved/blocked by Windows. Choose another port using BACKEND_PORT.`
  *Solution*: Another application (or a Windows reserved port range) is using 8742. Set a different port for the session:
  ```powershell
  $env:BACKEND_PORT = "8743"
  python scripts/run_prod.py
  ```
- **Another instance is already running**:
  `Another instance of Camera Monitor is already running on this data folder (C:\...\backend\data) with PID 12345.`
  *Solution*: The application enforces single-instance locking. Camera Monitor is already running under process ID `12345`. To inspect or stop the existing process:
  ```powershell
  tasklist /FI "PID eq 12345"
  taskkill /PID 12345
  ```

### Logs & Diagnostics
Camera Monitor writes structured logs to:
```text
backend/data/logs/camera-monitor.log
```
The file automatically rotates up to 5 backup files of 5 MiB each (`camera-monitor.log.1`, `camera-monitor.log.2`, etc.).

Status changes are logged whenever a camera's state transitions:
```text
2026-10-05 14:00:00,123 INFO [app.monitoring.engine] Camera 'Warehouse PTZ' (192.0.2.14) went OFFLINE (1 failed check)
2026-10-05 14:05:00,456 INFO [app.monitoring.engine] Camera 'Warehouse PTZ' (192.0.2.14) back ONLINE after 5 failed checks
```

## System Restarts

The monitoring engine stores its running state in SQLite (`monitoring_state`). If the admin PC or application restarts while monitoring was running, the engine automatically resumes probing on startup without requiring manual intervention.
