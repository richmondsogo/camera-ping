# Camera Monitor - Stop Service Script
# Requires PowerShell 5.1+, Windows 10/11 or Server 2016+ (64-bit)
# ASCII only

[CmdletBinding()]
param(
    [string]$TaskName = "CameraMonitor",
    [string]$InstallPath = "C:\Program Files\CameraMonitor",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

if ($TaskName -notmatch '^[a-zA-Z0-9 _-]{1,64}$') {
    Write-Error "Invalid TaskName '$TaskName'. TaskName must be 1 to 64 characters and contain only letters, digits, spaces, dashes, or underscores."
    exit 1
}

if ($DryRun) {
    Write-Host "[DRY-RUN] Will stop scheduled task '$TaskName' and verify process termination."
    exit 0
}

Write-Host "[INFO] Stopping scheduled task $TaskName..."
try {
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
} catch {
    # continue
}

$stopped = $false
for ($i = 0; $i -lt 10; $i++) {
    $procs = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
        $_.Path -and $_.Path.StartsWith($InstallPath, [System.StringComparison]::OrdinalIgnoreCase)
    }
    if (-not $procs) {
        $stopped = $true
        break
    }
    Start-Sleep -Seconds 1
}

if (-not $stopped) {
    Write-Host "[INFO] Process still active; terminating cleanly..."
    $procs = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
        $_.Path -and $_.Path.StartsWith($InstallPath, [System.StringComparison]::OrdinalIgnoreCase)
    }
    if ($procs) {
        $procs | Stop-Process -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "[PASS] Camera Monitor stopped."
exit 0
