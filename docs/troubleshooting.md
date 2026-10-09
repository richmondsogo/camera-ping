# Troubleshooting Guide

This guide shows you how to diagnose and resolve issues with Camera Monitor on the server room administration PC (Windows 10 Pro 64-bit, Version 10.0.19045, 22H2).

## Diagnosing Dashboard Banners and Alerts

When the dashboard detects an operational abnormality, it displays a colored banner across the interface.

### Resolving "Can't reach the server" Banner

- **Symptom**: A red banner displays: `Can't reach the server. Showing data from <time>. Retrying…`
- **Cause**: The React web interface cannot communicate with the local FastAPI backend service on port 8742 (or development port 8000).
- **Resolution**:
  1. Open Command Prompt as Administrator and change to `C:\Program Files\CameraMonitor\scripts`.
  2. Run `status.cmd` to check whether the backend process is running:
     ```cmd
     status.cmd
     ```
  3. If the task is stopped, start it:
     ```cmd
     start.cmd
     ```
  4. Inspect recent errors in the application log:
     ```powershell
     Get-Content -Path "C:\ProgramData\CameraMonitor\logs\camera-monitor.log" -Tail 30
     ```

**Result**: The dashboard reconnects and resumes live status polling within 5 seconds.

### Resolving "Monitoring looks stalled" Banner

- **Symptom**: A warning banner displays: `Monitoring looks stalled: no completed check since <time>.`
- **Cause**: The monitoring engine state is marked active, but no check cycle completed within `2 * interval + 30s`. This condition can occur if the host PC entered sleep mode or encountered thread pool exhaustion.
- **Resolution**:
  1. Click **Stop** in the monitoring panel.
  2. Wait 3 seconds.
  3. Click **Start** to initialize a fresh probing cycle.
  4. If the stall persists, verify that Windows sleep is disabled:
     ```cmd
     powercfg /query
     ```

**Result**: Camera Monitor initializes a new worker pool and completes an active probing cycle.

### Resolving "Every camera is offline" Banner

- **Symptom**: A banner displays: `Every camera is offline. If that's unexpected, check this PC's network connection.`
- **Cause**: All monitored cameras failed ICMP reachability checks simultaneously. This typically indicates a local network disconnection at the administration PC or a failed network switch.
- **Resolution**:
  1. Verify the physical Ethernet cable connection on the administration PC.
  2. Open Command Prompt and test reachability to the default network gateway:
     ```cmd
     ping <gateway-ip>
     ```
  3. Check power and link lights on the server room network switch.

**Result**: Once network connectivity is restored, cameras transition to **Online** during the next monitoring cycle.

### Responding to "Monitoring is stopped" Notice

- **Symptom**: An informational banner states: `Monitoring is stopped. Statuses below are from the last check.`
- **Cause**: An operator clicked **Stop**, or monitoring was never started after installation.
- **Resolution**:
  1. Click **Start** in the dashboard monitoring panel.

**Result**: Background probing resumes immediately.

## Resolving CSV Import Errors

Camera Monitor strictly validates CSV inventory files before importing any records.

### Resolving "The file isn't UTF-8" Alert

- **Symptom**: The browser displays: `The file isn't UTF-8. In Excel, use Save As and choose CSV UTF-8.`
- **Cause**: The file was saved in legacy Windows ANSI or Windows-1252 format.
- **Resolution**:
  1. Open the file in Microsoft Excel.
  2. Select **File > Save As**.
  3. In the **Save as type** dropdown, select **CSV UTF-8 (Comma delimited) (*.csv)**.
  4. Save the file and re-upload it.

**Result**: Camera Monitor parses the file and presents the validation preview.

### Resolving "Couldn't read the file" Error

- **Symptom**: The upload dialog displays: `Couldn't read the file. Close it in Excel and choose it again.`
- **Cause**: Microsoft Excel holds an exclusive write lock on the open CSV file.
- **Resolution**:
  1. Close the spreadsheet in Microsoft Excel.
  2. Return to the browser dialog and select the file again.

**Result**: The browser accesses the file without locking conflicts.

### Resolving "File size exceeds maximum limit of 1 MiB" Error

- **Symptom**: Upload fails with an HTTP 413 error: `File size exceeds maximum limit of 1 MiB.`
- **Cause**: The CSV file exceeds 1,048,576 bytes.
- **Resolution**:
  1. Confirm that the CSV contains only plain text camera inventory rows.
  2. Remove any embedded binary objects, images, or extraneous sheets.

**Result**: File size stays well within the 1 MiB threshold.

### Resolving Validation Table Errors

- **Symptom**: The validation screen displays: `1 problem found. Nothing was imported.` along with a table detailing **Line**, **Column**, and **Problem**.
- **Cause**: One or more rows contain invalid data (such as missing camera names, malformed IPv4 addresses, or duplicate IPs within the file or database).
- **Resolution**:
  1. Review the row numbers and error descriptions in the validation table.
  2. Open your CSV file and correct the reported rows.
     > [!NOTE]
     > Camera Monitor imports atomically: no rows are written to the database until 100% of rows pass validation.
  3. Save the corrected file as UTF-8 and upload it again.

**Result**: All rows pass validation and you can click **Import Cameras** to commit the changes.

### Resolving "Another camera with one of these IP addresses was added" Conflict

- **Symptom**: Clicking **Import Cameras** returns an HTTP 409 conflict error: `Another camera with one of these IP addresses was added in the meantime. Nothing was imported. Try again.`
- **Cause**: Another operator added a camera with an identical IP address between your validation preview and final confirmation.
- **Resolution**:
  1. Click **Export CSV** on the dashboard to review the current active inventory.
  2. Identify the duplicate IP address in your spreadsheet.
  3. Update or remove the conflicting row in your file, then re-import.

**Result**: Camera records import successfully without IP address collisions.

## Resolving Production Service Startup Failures

If the production service fails to start, use these diagnostic procedures.

### Identifying Launcher Exit Codes

When running in production, Camera Monitor logs fatal startup errors to `C:\ProgramData\CameraMonitor\logs\camera-monitor.log` and exits with one of the following codes:

- **Exit Code 2 (Configuration or build error)**:
  - *Cause*: Host address is not set to a loopback interface (`127.0.0.1` or `localhost`), or prebuilt frontend directory (`frontend/dist`) is missing.
  - *Resolution*: Ensure `C:\ProgramData\CameraMonitor\camera-monitor.env` uses `BACKEND_HOST=127.0.0.1`.
- **Exit Code 3 (Port occupied or reserved by Windows)**:
  - *Cause*: Port 8742 is occupied by another application or falls within a dynamic port exclusion range reserved by Windows.
  - *Resolution*: Change the port by adding `BACKEND_PORT=8743` to `C:\ProgramData\CameraMonitor\camera-monitor.env`, then run `start.cmd`.
- **Exit Code 4 (Instance lock collision)**:
  - *Cause*: Another instance of Camera Monitor is already active on the same data folder.
  - *Resolution*: The log names the holding process ID: `Another instance of Camera Monitor is already running on this data folder with PID <PID>.` Follow the hung process termination procedure below.
- **Exit Code 5 (Database migration error)**:
  - *Cause*: Alembic database migration failed.
  - *Resolution*: Inspect `camera-monitor.log` for SQLite schema errors or file permission issues on `data\camera_monitor.db`.

### Troubleshooting Scheduled Tasks

If Camera Monitor does not start after a system reboot:

1. Open Command Prompt as Administrator and change to `C:\Program Files\CameraMonitor\scripts`.
2. Check task status:
   ```cmd
   status.cmd
   ```
3. Inspect Windows Task Scheduler directly:
   - Run `taskschd.msc`.
   - In the left pane, navigate to **Task Scheduler Library > CameraMonitor**.
   - Check the **Last Run Result** column and inspect the **History** tab.
4. If task registration is corrupted, reinstall using the installer:
   ```cmd
   install.cmd
   ```

**Result**: The Scheduled Task is repaired and initialized under `NT AUTHORITY\SYSTEM`.

### Terminating Lingering or Hung Processes

Windows file locks are kernel-managed byte-range locks. When a process terminates—even during an unexpected crash—the operating system kernel releases the lock on `camera-monitor.lock` automatically.

If an instance hangs and refuses to exit:

1. Identify the process ID reported in the Exit Code 4 log message.
2. Locate the process in PowerShell:
   ```powershell
   tasklist /FI "PID eq <PID>"
   ```
3. Terminate the process:
   ```powershell
   taskkill /PID <PID>
   ```
   If the process does not terminate within 5 seconds, force termination:
   ```powershell
   taskkill /F /PID <PID>
   ```
4. Start the service:
   ```cmd
   start.cmd
   ```

**Result**: The new instance acquires the lock and starts cleanly.

### Refreshing Cached Browser Assets

- **Symptom**: The browser displays outdated interface elements or stale versions after an upgrade.
- **Cause**: The browser cached static single-page application assets.
- **Resolution**:
  1. Open the dashboard in Google Chrome or Microsoft Edge.
  2. Perform a hard refresh by pressing `Ctrl + F5` (or holding `Shift` while clicking **Reload**).

**Result**: The browser loads the latest frontend build from the local server.

## Resolving Local Development Server Issues

For developers running the application from source:

### Freeing Occupied Development Ports (8000 or 5173)

If `python scripts/dev.py` reports that port 8000 or 5173 is already in use:

1. Find the occupying process ID in PowerShell:
   ```powershell
   Get-NetTCPConnection -LocalPort 8000, 5173 -ErrorAction SilentlyContinue | Select-Object LocalPort, OwningProcess
   ```
2. Terminate the process using its process ID:
   ```powershell
   Stop-Process -Id <OwningProcessId>
   ```

**Result**: The port is released, allowing `scripts/dev.py` to bind successfully.

### Running Database Migrations Manually

If the development backend reports pending Alembic migrations:

1. Open PowerShell and navigate to the backend directory:
   ```powershell
   cd backend
   .\.venv\Scripts\alembic upgrade head
   ```

**Result**: The SQLite development database updates to the latest schema revision.

### Verifying Windows Ping Reachability Output

Camera Monitor parses output from the native Windows `ping.exe` utility, checking for the string `"TTL="` in standard output.

To test reachability parsing directly from the command line:

1. Run `ping.exe` against a known camera IP on the office subnet:
   ```cmd
   ping.exe -n 1 -w 1000 192.0.2.10
   ```
2. Verify that the response includes `TTL=`:
   ```text
   Reply from 192.0.2.10: bytes=32 time<1ms TTL=64
   ```

**Result**: Confirms that local Windows ICMP echo requests succeed and match expected parsing rules.

For ongoing maintenance routines and backup schedules, consult the [Operations & Maintenance Guide](maintenance.md). For complete installation instructions, see the [Installation Guide](install-guide.md).
