# Camera Monitor - Start Service Script
# Requires PowerShell 5.1+, Windows 10/11 or Server 2016+ (64-bit)
# ASCII only

[CmdletBinding()]
param(
    [string]$TaskName = "CameraMonitor",
    [int]$Port = 8742,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

if ($TaskName -notmatch '^[a-zA-Z0-9 _-]{1,64}$') {
    Write-Error "Invalid TaskName '$TaskName'. TaskName must be 1 to 64 characters and contain only letters, digits, spaces, dashes, or underscores."
    exit 1
}

if ($DryRun) {
    Write-Host "[DRY-RUN] Will start scheduled task '$TaskName' and verify health on port $Port."
    exit 0
}

Write-Host "[INFO] Starting scheduled task $TaskName..."
Start-ScheduledTask -TaskName $TaskName

$healthy = $false
for ($i = 0; $i -lt 15; $i++) {
    Start-Sleep -Seconds 1
    try {
        $req = [System.Net.WebRequest]::Create("http://127.0.0.1:$Port/api/health")
        $req.Timeout = 1000
        $res = $req.GetResponse()
        if ($res.StatusCode -eq 200) {
            $healthy = $true
            $res.Close()
            break
        }
        $res.Close()
    } catch {
        # continue waiting
    }
}

if ($healthy) {
    Write-Host "[PASS] Camera Monitor is running and healthy on http://127.0.0.1:$Port"
    exit 0
} else {
    Write-Host "[FAIL] Camera Monitor did not respond to health check within 15 seconds."
    exit 1
}
