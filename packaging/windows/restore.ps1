# Camera Monitor - Database Restore Script
# Requires PowerShell 5.1+, Windows 10/11 or Server 2016+ (64-bit)
# ASCII only

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$BackupFile,
    [string]$HomePath = "C:\ProgramData\CameraMonitor",
    [string]$InstallPath = "C:\Program Files\CameraMonitor",
    [string]$TaskName = "CameraMonitor",
    [switch]$DryRun,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

function Write-Info($msg) {
    Write-Host "[INFO] $msg"
}

function Write-Pass($msg) {
    Write-Host "[PASS] $msg"
}

if (-not (Test-Path $BackupFile)) {
    Write-Error "Backup file does not exist: $BackupFile"
    exit 1
}

if ($DryRun) {
    Write-Host "[DRY-RUN] Will verify $BackupFile, snapshot current database, and restore."
    exit 0
}

# 1. Ensure service is stopped
$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($task -and $task.State -eq "Running") {
    Write-Error "Cannot restore while $TaskName task is running. Please run .\stop.cmd first."
    exit 1
}

$procs = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -and $_.Path.StartsWith($InstallPath, [System.StringComparison]::OrdinalIgnoreCase)
}
if ($procs) {
    Write-Error "Cannot restore while CameraMonitor python process is active. Please run .\stop.cmd first."
    exit 1
}

# 2. Verify backup file integrity
$pythonExe = Join-Path $InstallPath "python\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pythonCmd = Get-Command "python" -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        $pythonExe = $pythonCmd.Source
    } else {
        Write-Error "Could not locate python.exe to test database integrity."
        exit 1
    }
}

Write-Info "Verifying backup file integrity: $BackupFile..."
$verifyScript = "import sqlite3, sys; d = sqlite3.connect(sys.argv[1]); c = d.cursor(); res = c.execute('PRAGMA integrity_check;').fetchall(); d.close(); sys.exit(0 if res == [('ok',)] else 1)"
& $pythonExe -c $verifyScript $BackupFile
if ($LASTEXITCODE -ne 0) {
    Write-Error "Backup file failed PRAGMA integrity_check. Restore aborted."
    exit 1
}

# 3. Snapshot existing database
$targetDb = Join-Path $HomePath "data\camera_monitor.db"
if (Test-Path $targetDb) {
    $snapshotPath = "$targetDb.before-restore"
    Write-Info "Saving pre-restore snapshot to $snapshotPath..."
    Copy-Item -Path $targetDb -Destination $snapshotPath -Force
}

# 4. Replace database file and clear WAL/SHM
Write-Info "Restoring database from $BackupFile..."
Copy-Item -Path $BackupFile -Destination $targetDb -Force

$walFile = "$targetDb-wal"
if (Test-Path $walFile) {
    Remove-Item -Path $walFile -Force -ErrorAction SilentlyContinue
}
$shmFile = "$targetDb-shm"
if (Test-Path $shmFile) {
    Remove-Item -Path $shmFile -Force -ErrorAction SilentlyContinue
}

Write-Pass "Database successfully restored from $BackupFile"
Write-Info "Snapshot of previous database saved to $targetDb.before-restore"
Write-Info "You may now start the service by running .\start.cmd."
exit 0
