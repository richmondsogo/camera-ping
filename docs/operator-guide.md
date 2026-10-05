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

## System Restarts

The monitoring engine stores its running state in SQLite (`monitoring_state`). If the admin PC or application restarts while monitoring was running, the engine automatically resumes probing on startup without requiring manual intervention.
