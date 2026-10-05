# Troubleshooting Guide

This guide describes common symptoms, causes, and solutions verified in Camera Monitor.

## Dashboard Banners & Notices

### Banner: `Can't reach the server. Showing data from <time>. Retrying…`
- **Symptom**: Red warning banner at top of dashboard; polling status fails.
- **Cause**: The React frontend is unable to reach the FastAPI backend on port 8000 (or port 18000 in E2E).
- **Fix**: Check if the backend server process crashed or was stopped. Restart it with `python scripts/dev.py`.

### Banner: `Monitoring looks stalled: no completed check since <time>.`
- **Symptom**: Red warning banner indicating monitoring has not completed a cycle within `2 * interval + 30s`.
- **Cause**: Background ping threads encountered an unhandled exception or the host system went to sleep / entered extreme CPU throttling.
- **Fix**: Click **Stop**, wait 3 seconds, then click **Start** to restart the monitoring thread. Check backend logs for unexpected process execution errors.

### Banner: `Every camera is offline. If that's unexpected, check this PC's network connection.`
- **Symptom**: Gray status banner appears when 2 or more cameras are monitored and 100% of them are reported Offline.
- **Cause**: The admin PC's network adapter is disconnected, the local subnet gateway is unreachable, or a switch failure occurred.
- **Fix**: Check physical Ethernet cabling on the admin PC. Verify network connectivity by pinging the local gateway manually. *(verify at the office)*

### Notice: `Monitoring is stopped. Statuses below are from the last check.`
- **Symptom**: Muted notice below the monitoring panel.
- **Cause**: Monitoring was stopped manually via the **Stop** button, or the engine has never been started.
- **Fix**: Click the **Start** button in the monitoring panel to resume reachability checks.

## CSV Import Issues

### Error: `The file isn't UTF-8. In Excel, use Save As and choose CSV UTF-8.`
- **Symptom**: CSV upload fails immediately with an encoding alert.
- **Cause**: The uploaded file was saved using Windows-1252 or ANSI encoding (default legacy Excel CSV format).
- **Fix**: In Microsoft Excel, select **File > Save As**, open the format dropdown, and select **CSV UTF-8 (Comma delimited) (*.csv)**.

### Error: `Couldn't read the file. Close it in Excel and choose it again.`
- **Symptom**: File selection fails with a browser file access error.
- **Cause**: Microsoft Excel has an exclusive write lock on the open file.
- **Fix**: Close the workbook in Excel, return to the browser dialog, and choose the file again.

### Error: `File size exceeds maximum limit of 1 MiB.`
- **Symptom**: Upload rejected with payload too large error (HTTP 413).
- **Cause**: Uploaded CSV file exceeds 1,048,576 bytes.
- **Fix**: Ensure the CSV contains only plain text camera records without embedded binary data or extraneous sheets.

### Error: `1 problem found. Nothing was imported.` (Validation Table)
- **Symptom**: Error table lists specific Line, Column, and Problem entries; database remains unchanged.
- **Cause**: One or more rows violated field constraints (missing name, invalid IPv4 address format, duplicate IP address within file or database).
- **Fix**: Correct the rows identified in the table. The entire file is validated atomically; re-upload once all rows are fixed.

### Error: `Another camera with one of these IP addresses was added in the meantime. Nothing was imported. Try again.`
- **Symptom**: Server returns HTTP 409 conflict upon import confirmation.
- **Cause**: A camera with an identical IP was added in another session between validation preview and commit.
- **Fix**: Export the current inventory to identify the conflicting IP, update your CSV, and re-import.

## Server & Startup Issues

### Dev Port Already in Use (Port 8000 or 5173)
- **Symptom**: `scripts/dev.py` fails to bind or exits immediately.
- **Cause**: A previous server instance was orphaned or another local service occupies the port.
- **Fix**: Identify and terminate the occupying process on Windows:
  ```powershell
  Get-NetTCPConnection -LocalPort 8000, 5173 -ErrorAction SilentlyContinue | Select-Object LocalPort, OwningProcess
  Stop-Process -Id <OwningProcessId>
  ```

### Backend Refuses to Start Due to Migration Errors
- **Symptom**: FastAPI fails during startup with an Alembic database error.
- **Cause**: The SQLite database file schema does not match current Alembic revisions.
- **Fix**: Run database migrations:
  ```powershell
  cd backend
  .\.venv\Scripts\alembic upgrade head
  ```

### Non-English Windows Ping Output Mismatch *(verify at the office)*
- **Symptom**: Reachable cameras reported as Offline on target admin PC.
- **Cause**: The online rule requires `"TTL="` in stdout. If the Windows OS language produces translated output without TTL, reachability parsing could fail.
- **Fix**: Verify raw `ping.exe` output on the target PC and update probe matching if needed. *(verify at the office)*
