# Camera Monitor - Database Backup Script
# Requires PowerShell 5.1+, Windows 10/11 or Server 2016+ (64-bit)
# ASCII only

[CmdletBinding()]
param(
    [string]$HomePath = "C:\ProgramData\CameraMonitor",
    [string]$InstallPath = "C:\Program Files\CameraMonitor",
    [int]$KeepCount = 14,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Write-Info($msg) {
    Write-Host "[INFO] $msg"
}

function Write-Pass($msg) {
    Write-Host "[PASS] $msg"
}

$sourceDb = Join-Path $HomePath "data\camera_monitor.db"
$backupsDir = Join-Path $HomePath "backups"

if (-not (Test-Path $sourceDb)) {
    Write-Error "Database not found at $sourceDb. Nothing to backup."
    exit 1
}

$timestamp = (Get-Date).ToString("yyyyMMdd-HHmmss")
$targetDb = Join-Path $backupsDir "camera_monitor-$timestamp.db"

if ($DryRun) {
    Write-Host "[DRY-RUN] Will backup $sourceDb to $targetDb and keep newest $KeepCount backups."
    exit 0
}

if (-not (Test-Path $backupsDir)) {
    New-Item -ItemType Directory -Path $backupsDir -Force | Out-Null
}

# Locate python executable
$pythonExe = Join-Path $InstallPath "python\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pythonCmd = Get-Command "python" -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        $pythonExe = $pythonCmd.Source
    } else {
        Write-Error "Could not locate python.exe to run SQLite backup API."
        exit 1
    }
}

Write-Info "Executing online backup from $sourceDb to $targetDb..."
$backupScript = "import sqlite3, sys; s = sqlite3.connect(sys.argv[1]); d = sqlite3.connect(sys.argv[2]); s.backup(d); d.close(); s.close(); d2 = sqlite3.connect(sys.argv[2]); c = d2.cursor(); res = c.execute('PRAGMA integrity_check;').fetchall(); d2.close(); sys.exit(0 if res == [('ok',)] else 1)"

$proc = Start-Process -FilePath $pythonExe -ArgumentList @("-c", $backupScript, $sourceDb, $targetDb) -NoNewWindow -Wait -PassThru

if ($proc.ExitCode -ne 0) {
    Write-Error "Backup or integrity check failed with exit code $($proc.ExitCode)."
    if (Test-Path $targetDb) {
        Remove-Item -Path $targetDb -Force -ErrorAction SilentlyContinue
    }
    exit 1
}

$backupSize = (Get-Item $targetDb).Length
Write-Pass "Backup created successfully: $targetDb ($backupSize bytes)"

# Rotate backups: keep newest $KeepCount
$allBackups = Get-ChildItem -Path $backupsDir -Filter "camera_monitor-*.db" | Sort-Object Name -Descending
if ($allBackups.Count -gt $KeepCount) {
    $toDelete = $allBackups | Select-Object -Skip $KeepCount
    foreach ($item in $toDelete) {
        Write-Info "Rotating old backup: $($item.Name)..."
        Remove-Item -Path $item.FullName -Force -ErrorAction SilentlyContinue
    }
    Write-Info "Rotated backups (kept newest $KeepCount)."
}

exit 0
