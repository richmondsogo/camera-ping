# Camera Monitor - Service Status Script
# Requires PowerShell 5.1+, Windows 10/11 or Server 2016+ (64-bit)
# ASCII only

[CmdletBinding()]
param(
    [string]$TaskName = "CameraMonitor",
    [string]$BackupTaskName = "CameraMonitor Backup",
    [int]$Port = 8742,
    [string]$HomePath = "C:\ProgramData\CameraMonitor",
    [switch]$DryRun
)

$ErrorActionPreference = "Continue"

if ($DryRun) {
    Write-Host "[DRY-RUN] Will inspect scheduled task '$TaskName', processes, and API health."
    exit 0
}

Write-Host "============================================================"
Write-Host "Camera Monitor - System & Service Status"
Write-Host "============================================================"

# Task Scheduler Status
$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($task) {
    $info = Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction SilentlyContinue
    Write-Host "Task Name:        $TaskName"
    Write-Host "Task State:       $($task.State)"
    Write-Host "Last Run Time:    $($info.LastRunTime)"
    Write-Host "Last Result:      $($info.LastTaskResult)"
} else {
    Write-Host "Task Name:        $TaskName (NOT REGISTERED)"
}

$bTask = Get-ScheduledTask -TaskName $BackupTaskName -ErrorAction SilentlyContinue
if ($bTask) {
    Write-Host "Backup Task:      $BackupTaskName ($($bTask.State))"
}

# Process Status
$procs = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -and ($_.Path -like "*CameraMonitor*")
}
if ($procs) {
    foreach ($p in $procs) {
        $wsMB = [math]::Round($p.WorkingSet64 / 1MB, 2)
        Write-Host "Process PID:      $($p.Id) (WorkingSet: ${wsMB} MB, StartTime: $($p.StartTime))"
    }
} else {
    Write-Host "Process:          No CameraMonitor python processes running."
}

# Health & Monitoring API
$healthy = $false
try {
    $req = [System.Net.WebRequest]::Create("http://127.0.0.1:$Port/api/health")
    $req.Timeout = 1500
    $res = $req.GetResponse()
    if ($res.StatusCode -eq 200) {
        $healthy = $true
        Write-Host "Health Endpoint:  ONLINE (200 OK at http://127.0.0.1:$Port/api/health)"
    }
    $res.Close()
} catch {
    Write-Host "Health Endpoint:  OFFLINE or unreachable on port $Port"
}

# Monitoring Engine Status
if ($healthy) {
    try {
        $req = [System.Net.WebRequest]::Create("http://127.0.0.1:$Port/api/monitoring/status")
        $req.Timeout = 1500
        $res = $req.GetResponse()
        $reader = New-Object System.IO.StreamReader($res.GetResponseStream())
        $body = $reader.ReadToEnd()
        $res.Close()
        Write-Host "Monitoring State: $body"
    } catch {
        # continue
    }
}

# Log File info
$logFile = Join-Path $HomePath "logs\camera-monitor.log"
if (Test-Path $logFile) {
    $logItem = Get-Item $logFile
    Write-Host "Log File:         $logFile ($([math]::Round($logItem.Length / 1KB, 2)) KB, Modified: $($logItem.LastWriteTime))"
}

Write-Host "============================================================"
exit 0
