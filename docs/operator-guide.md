# Operator Guide

This guide shows you how to operate Camera Monitor to track office network camera availability from the administration PC in the server room (Windows 10 Pro 64-bit, Version 10.0.19045, 22H2).

## Accessing the Dashboard

You can access the Camera Monitor dashboard locally on the server room PC:

- **Desktop shortcut**: Double-click the **Camera Monitor** shortcut on the Windows desktop.
- **Web browser**: Open any modern browser and navigate to `http://127.0.0.1:8742`.

> [!NOTE]
> Always use `http://127.0.0.1:8742`. Camera Monitor binds exclusively to IPv4 loopback (`127.0.0.1`) and denies external network traffic.

## Navigating the Dashboard

The dashboard provides a real-time overview of camera reachability across the office network.

### Interpreting Camera Statuses

Each camera row displays one of three reachability statuses:

- **Online (green)**: The camera is reachable and replied to ICMP echo requests.
- **Offline (red)**: The camera failed to reply to ICMP echo requests. The badge indicates the failure duration: `(1 check)` or `(N checks)`.
- **Unknown (gray)**: The camera is newly added or edited and has not yet been probed in an active monitoring cycle.

### Reading Monitoring Indicators

The top monitoring panel provides operational controls and cycle information:

- **Summary counts**: Displays total monitored cameras and counts for `online`, `offline`, and `unknown` devices.
- **Last check**: Displays the completion time of the previous probing cycle (for example, `Last check 10:45 AM`).
- **Next check**: Displays a countdown to the next scheduled probing cycle (for example, `Next check in 45s`).
- **Checks every**: Displays the configured probing interval (for example, `Checks every 1 minute`).

### Responding to Dashboard Banners

The dashboard displays situational banners when attention is required:

- **Stopped notice**:
  `Monitoring is stopped. Statuses below are from the last check.`
  - **Action**: Click **Start** to resume automated reachability checks.
- **Connection lost banner**:
  `Can't reach the server. Showing data from <time>. Retrying…`
  - **Action**: The dashboard cannot communicate with the local backend service. The browser retries automatically. If the condition persists, verify the backend process is running using `scripts\status.cmd`.
- **Stalled banner**:
  `Monitoring looks stalled: no completed check since <time>.`
  - **Action**: Monitoring is marked as active, but no cycle completed recently. Click **Stop**, wait 3 seconds, and click **Start** to restart the monitoring thread.
- **All offline banner**:
  `Every camera is offline. If that's unexpected, check this PC's network connection.`
  - **Action**: Verify that the admin PC network cable is connected and that the local network switch is powered on.

## Controlling Monitoring Cycles

You can start and stop automated ICMP checks at any time.

### Starting Monitoring

1. Click **Start** in the monitoring panel.
2. Observe the indicator state change to `Monitoring running` with a green indicator.

**Result**: Camera Monitor begins background reachability cycles at the configured interval.

### Stopping Monitoring

1. Click **Stop** in the monitoring panel.
2. Observe the indicator state change to `Monitoring stopped` with a gray indicator.

**Result**: Camera Monitor pauses probing. The dashboard continues displaying statuses from the final check cycle.

## Managing Cameras

You can add, edit, or delete camera records directly in the dashboard interface.

### Adding a Camera

Before you begin, ensure you have the camera name and its static IPv4 address.

1. Click **Add Camera** in the toolbar.
2. Enter the camera name in the **Camera Name** field.
3. Optional: Enter the physical location and description.
4. Enter the static IPv4 address in the **IP Address** field.
5. Click **Add Camera**.

**Result**: The new camera appears in the table with `Unknown` status until the next probing cycle runs.

### Editing a Camera

1. Locate the camera row and click **Edit**.
2. Update the name, location, or description as needed.
3. If updating the IP address, observe the warning:
   `Changing the IP address resets this camera's reachability statistics and monitoring history.`
4. Click **Save Changes**.

**Result**: Camera Monitor saves the updated attributes. If you changed the IP address, its status resets to `Unknown` and failure counts clear.

### Deleting a Camera

1. Locate the camera row and click **Delete**.
2. When the confirmation prompt appears (`Are you sure you want to delete camera "<Name>" (<IP>)? This action cannot be undone.`), click **Delete Camera**.

**Result**: Camera Monitor permanently removes the camera and its historical reachability records from the database.

## Importing and Exporting Camera Inventory

You can manage large camera inventories through CSV files.

### Importing Cameras from CSV

Before you begin, prepare a CSV file formatted as UTF-8 with exactly four header columns:
`camera_name,location,description,ip_address`

For detailed formatting rules, see the [CSV Format Specification](csv-format.md).

1. Click **Import CSV** in the toolbar.
2. If you create or edit your file in Microsoft Excel, click **File > Save As** and choose **CSV UTF-8 (Comma delimited) (*.csv)**.
3. Select your file in the upload dialog. Camera Monitor validates all rows automatically in a dry run.
4. If validation errors occur, inspect the table displaying **Line**, **Column**, and **Problem**.
   > [!IMPORTANT]
   > Camera Monitor imports nothing if any row fails validation. Correct all reported errors in your file and select it again.
5. Once validation passes, review the row preview and click **Import Cameras**.

**Result**: Camera Monitor adds the validated camera records to the inventory.

### Exporting Cameras to CSV

1. Click **Export CSV** in the toolbar.

**Result**: Your browser downloads a CSV file containing all camera inventory fields, current reachability status, and timestamps.

## Configuring Settings

Click **Settings** in the navigation header to adjust operational preferences.

### Adjusting Check Intervals

1. Navigate to **Settings**.
2. Under **Check Interval**, select a preset duration (`10 seconds`, `30 seconds`, `1 minute`, `2 minutes`, `5 minutes`, or `10 minutes`) or select `Custom…`.
3. If using `Custom…`, enter an interval between 10 seconds and 365 days.
   > [!NOTE]
   > Selecting an interval of 1 hour or greater displays the advisory notice: `Outages may take up to <duration> to detect.`

**Result**: The monitoring engine applies the new interval immediately to subsequent cycles.

### Selecting Appearance Theme

1. Navigate to **Settings**.
2. Under **Appearance**, select either **Light** or **Dark**.

**Result**: The interface applies the selected theme immediately.

## Managing the Production Service

In production, Camera Monitor runs as an automated background service managed by Windows Task Scheduler under `NT AUTHORITY\SYSTEM` (principal `S-1-5-18`).

### Running Service Commands

Open Command Prompt or PowerShell as Administrator and change to `C:\Program Files\CameraMonitor\scripts`:

- **Check service state**:
  ```cmd
  status.cmd
  ```
  Displays Windows task state, process ID (PID), memory usage, and monitoring engine status.
- **Start the service**:
  ```cmd
  start.cmd
  ```
- **Stop the service**:
  ```cmd
  stop.cmd
  ```
- **Trigger immediate backup**:
  ```cmd
  backup.cmd
  ```

For detailed service procedures, see the [Operations & Maintenance Guide](maintenance.md). For installation details, see the [Installation Guide](install-guide.md).

### Resolving Startup Messages

- **Port already in use or reserved**:
  `Port 8742 is already in use or reserved/blocked by Windows. Choose another port using BACKEND_PORT.`
  - **Resolution**: Another process or Windows exclusion holds port 8742. Set a different port in `C:\ProgramData\CameraMonitor\camera-monitor.env` (or set `$env:BACKEND_PORT = "8743"`).
- **Another instance is already running**:
  `Another instance of Camera Monitor is already running on this data folder with PID 12345.`
  - **Resolution**: Camera Monitor enforces single-instance locking. Check running instances using `scripts\status.cmd` or stop active processes using `scripts\stop.cmd`.

### Viewing Application Logs

Camera Monitor writes structured logs to:

- Production: `C:\ProgramData\CameraMonitor\logs\camera-monitor.log`
- Development: `backend/data/logs/camera-monitor.log`

The logging system automatically rotates up to 5 archived files (`camera-monitor.log.1` through `.5`).

Each camera state transition is logged with failure metrics:
```text
2026-10-05 14:00:00,123 INFO [app.monitoring.engine] Camera 'Warehouse PTZ' (192.0.2.14) went OFFLINE (1 failed check)
2026-10-05 14:05:00,456 INFO [app.monitoring.engine] Camera 'Warehouse PTZ' (192.0.2.14) back ONLINE after 5 failed checks
```

### Handling System Restarts

The monitoring engine records its operational state in SQLite (`monitoring_state`). When the admin PC reboots, the service starts automatically at boot with a 30-second delay. If monitoring was running prior to shutdown, the engine automatically resumes probing without requiring operator intervention.

For quick reference on index cards in the server room, consult the [Operator Quick Card](operator-card.md). For unexpected behavior and error codes, consult the [Troubleshooting Guide](troubleshooting.md).
