# Camera Monitor - Windows Installation Script
# Requires PowerShell 5.1+, Windows 10/11 or Server 2016+ (64-bit)
# ASCII only

[CmdletBinding()]
param(
    [Alias("InstallDir")][string]$InstallPath = "C:\Program Files\CameraMonitor",
    [Alias("HomeDir")][string]$HomePath = "C:\ProgramData\CameraMonitor",
    [string]$TaskName = "CameraMonitor",
    [string]$BackupTaskName = "$TaskName Backup",
    [int]$Port = 8742,
    [switch]$SkipPowerSettings,
    [switch]$SkipTaskStart,
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

function Write-Fail($msg) {
    Write-Host "[FAIL] $msg"
}

# 1. Validate TaskName format
if ($TaskName -notmatch '^[a-zA-Z0-9 _-]{1,64}$') {
    Write-Error "Invalid TaskName '$TaskName'. TaskName must be 1 to 64 characters and contain only letters, digits, spaces, dashes, or underscores."
    exit 1
}

# 2. Elevation check
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
$isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if ($DryRun -and ($env:CAMERA_MONITOR_TEST_ELEVATED -eq "0" -or $env:CAMERA_MONITOR_TEST_ELEVATED -eq "1")) {
    $isAdmin = ($env:CAMERA_MONITOR_TEST_ELEVATED -eq "1")
}

if (-not $isAdmin) {
    if ($DryRun) {
        Write-Host "[DRY-RUN] Notice: Script is running without elevation (Administrator required for live install)."
    } else {
        Write-Error "Administrator privileges are required. Please run this script in an elevated PowerShell session (Run as administrator)."
        exit 1
    }
}

# 2. Bundle payload pre-flight validation
$scriptDir = $PSScriptRoot
$bundleRoot = (Resolve-Path "$scriptDir\..").Path
$bundlePython = Join-Path $bundleRoot "python"
$bundleApp = Join-Path $bundleRoot "app"
$bundleFrontend = Join-Path $bundleRoot "frontend\dist"

$hasBundlePayload = (Test-Path $bundlePython) -and (Test-Path $bundleApp) -and (Test-Path $bundleFrontend)

if (-not $hasBundlePayload) {
    $repoCandidate = $null
    try {
        $repoCandidate = (Resolve-Path "$scriptDir\..\.." -ErrorAction SilentlyContinue).Path
    } catch {
        $repoCandidate = $null
    }
    $isRepo = $false
    if ($repoCandidate) {
        $isRepo = Test-Path (Join-Path $repoCandidate "backend\app")
    }

    if ($DryRun -and $isRepo) {
        $bundleRoot = $repoCandidate
    } else {
        Write-Error "Cannot locate required bundle directories (..\python, ..\app, ..\frontend\dist) at $bundleRoot. install.ps1 must be run from an extracted distribution bundle (referencing scripts/build_bundle.py)."
        exit 1
    }
}

if ($DryRun) {
    $pythonExe = Join-Path $InstallPath "python\python.exe"
    $frontendDist = Join-Path $InstallPath "frontend\dist"
    $serveArgs = "-m app.serve --home `"$HomePath`" --frontend-dist `"$frontendDist`""
    $backupScript = Join-Path $InstallPath "scripts\backup.ps1"

    Write-Host "============================================================"
    Write-Host "Camera Monitor - Installer Dry Run Plan"
    Write-Host "============================================================"
    Write-Host "Bundle Source:       $bundleRoot"
    Write-Host "Target Install Path: $InstallPath"
    Write-Host "Target Home Path:    $HomePath"
    Write-Host "Port:                $Port"
    Write-Host "Scheduled Task:      $TaskName"
    Write-Host "  Principal:         S-1-5-18 (Highest run level)"
    Write-Host "  Trigger:           AtStartup (Delay: 30s)"
    Write-Host "  Action:            $pythonExe $serveArgs"
    Write-Host "  WorkingDirectory:  $InstallPath\app"
    Write-Host "  Settings:          ExecutionTimeLimit=PT0S, MultipleInstances=IgnoreNew, StartWhenAvailable, AllowStartIfOnBatteries, DontStopIfGoingOnBatteries, RestartInterval=PT1M, RestartCount=999"
    Write-Host "Backup Task:         $BackupTaskName"
    Write-Host "  Principal:         S-1-5-18 (Highest run level)"
    Write-Host "  Trigger:           Daily 03:00"
    Write-Host "  Action:            powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$backupScript`" -HomePath `"$HomePath`" -InstallPath `"$InstallPath`""
    Write-Host "  Settings:          AllowStartIfOnBatteries, DontStopIfGoingOnBatteries, StartWhenAvailable, ExecutionTimeLimit=PT2H"
    Write-Host "Power Settings:      $(-not $SkipPowerSettings) (Saves previous timeouts to $HomePath\power-before.txt)"
    Write-Host "Auto Start:          $(-not $SkipTaskStart)"
    Write-Host "============================================================"
    Write-Host "[DRY-RUN] Preflight checks and plan validated successfully."
    exit 0
}

# 3. Preflight: Disk space check (>= 2GB free on install drive)
try {
    $installRoot = [System.IO.Path]::GetPathRoot($InstallPath)
    $drive = Get-PSDrive ($installRoot.TrimEnd(":\")) -ErrorAction SilentlyContinue
    if ($drive -and $drive.Free -lt 2147483648) {
        Write-Error "Insufficient disk space on $installRoot. At least 2GB free required."
        exit 1
    }
} catch {
    Write-Warning "Could not verify disk space on target drive."
}

# 4. Port availability check
$portOpen = $false
try {
    $tcp = New-Object System.Net.Sockets.TcpClient
    $iar = $tcp.BeginConnect("127.0.0.1", $Port, $null, $null)
    $success = $iar.AsyncWaitHandle.WaitOne(500, $false)
    if ($success) {
        $tcp.EndConnect($iar)
        $portOpen = $true
    }
    $tcp.Close()
} catch {
    $portOpen = $false
}

$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Info "Existing installation detected ($TaskName). Stopping existing task for upgrade..."
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
} elseif ($portOpen) {
    Write-Error "Port $Port is already in use by another process. Choose another port or stop the conflicting service."
    exit 1
}

# 5. Handle upgrade directory rotation
if (Test-Path $InstallPath) {
    $prevPath = "$InstallPath.previous"
    if (Test-Path $prevPath) {
        Remove-Item -Path $prevPath -Recurse -Force
    }
    Write-Info "Backing up previous installation to $prevPath..."
    Move-Item -Path $InstallPath -Destination $prevPath -Force
}

# 6. Copy bundle files to InstallPath
Write-Info "Installing program files to $InstallPath..."
New-Item -ItemType Directory -Path $InstallPath -Force | Out-Null
Copy-Item -Path "$bundleRoot\python" -Destination "$InstallPath\python" -Recurse -Force
Copy-Item -Path "$bundleRoot\app" -Destination "$InstallPath\app" -Recurse -Force
Copy-Item -Path "$bundleRoot\frontend" -Destination "$InstallPath\frontend" -Recurse -Force
Copy-Item -Path "$bundleRoot\scripts" -Destination "$InstallPath\scripts" -Recurse -Force
if (Test-Path "$bundleRoot\docs") {
    Copy-Item -Path "$bundleRoot\docs" -Destination "$InstallPath\docs" -Recurse -Force
}
if (Test-Path "$bundleRoot\VERSION") {
    Copy-Item -Path "$bundleRoot\VERSION" -Destination "$InstallPath\VERSION" -Force
}
if (Test-Path "$bundleRoot\CHANGELOG.md") {
    Copy-Item -Path "$bundleRoot\CHANGELOG.md" -Destination "$InstallPath\CHANGELOG.md" -Force
}
if (Test-Path "$bundleRoot\README-FIRST.txt") {
    Copy-Item -Path "$bundleRoot\README-FIRST.txt" -Destination "$InstallPath\README-FIRST.txt" -Force
}

# 7. Initialize HomePath (C:\ProgramData\CameraMonitor)
Write-Info "Configuring data and log directory at $HomePath..."
New-Item -ItemType Directory -Path (Join-Path $HomePath "data") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $HomePath "logs") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $HomePath "backups") -Force | Out-Null

$envFile = Join-Path $HomePath "camera-monitor.env"
if (-not (Test-Path $envFile)) {
    $envContent = @"
# Camera Monitor Environment Configuration
BACKEND_PORT=$Port
MONITOR_INTERVAL_SECONDS=60
"@
    [System.IO.File]::WriteAllText($envFile, $envContent, [System.Text.Encoding]::ASCII)
    Write-Info "Created initial configuration file at $envFile"
}

# 8. Register Scheduled Tasks
Write-Info "Registering boot-time Scheduled Task: $TaskName..."
$pythonExe = Join-Path $InstallPath "python\python.exe"
$frontendDist = Join-Path $InstallPath "frontend\dist"
$serveArgs = "-m app.serve --home `"$HomePath`" --frontend-dist `"$frontendDist`""

$action = New-ScheduledTaskAction `
    -Execute $pythonExe `
    -Argument $serveArgs `
    -WorkingDirectory "$InstallPath\app"

$trigger = New-ScheduledTaskTrigger -AtStartup
$trigger.Delay = "PT30S"

$principal = New-ScheduledTaskPrincipal `
    -UserId "S-1-5-18" `
    -LogonType ServiceAccount `
    -RunLevel Highest

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Force | Out-Null

# Backup Task: Daily at 03:00
Write-Info "Registering daily backup Scheduled Task: $BackupTaskName..."
$backupScript = Join-Path $InstallPath "scripts\backup.ps1"
$backupAction = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$backupScript`" -HomePath `"$HomePath`" -InstallPath `"$InstallPath`""

$backupTrigger = New-ScheduledTaskTrigger -Daily -At "03:00"
$backupSettings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask `
    -TaskName $BackupTaskName `
    -Action $backupAction `
    -Trigger $backupTrigger `
    -Principal $principal `
    -Settings $backupSettings `
    -Force | Out-Null

# 9. Power Settings
if (-not $SkipPowerSettings) {
    Write-Info "Configuring power policy to prevent standby sleep on AC power..."
    $powerBeforeFile = Join-Path $HomePath "power-before.txt"
    try {
        $standbyAc = 0
        $hibernateAc = 0
        $qStandby = & powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE 2>$null
        if ($qStandby) {
            foreach ($line in $qStandby) {
                if ($line -match "Current AC Power Setting Index:\s+(0x[0-9a-fA-F]+)") {
                    $standbyAc = [int]([Convert]::ToInt32($matches[1], 16) / 60)
                }
            }
        }
        $qHibernate = & powercfg /query SCHEME_CURRENT SUB_SLEEP HIBERNATEIDLE 2>$null
        if ($qHibernate) {
            foreach ($line in $qHibernate) {
                if ($line -match "Current AC Power Setting Index:\s+(0x[0-9a-fA-F]+)") {
                    $hibernateAc = [int]([Convert]::ToInt32($matches[1], 16) / 60)
                }
            }
        }
        if (-not (Test-Path $powerBeforeFile)) {
            $pbContent = "STANDBY_TIMEOUT_AC=$standbyAc`r`nHIBERNATE_TIMEOUT_AC=$hibernateAc`r`n"
            [System.IO.File]::WriteAllText($powerBeforeFile, $pbContent, [System.Text.Encoding]::ASCII)
            Write-Info "Saved original AC power timeouts to $powerBeforeFile (standby=$standbyAc min, hibernate=$hibernateAc min)"
        }
        & powercfg /change standby-timeout-ac 0
        & powercfg /change monitor-timeout-ac 15
    } catch {
        Write-Warning "Could not update power configuration: $_"
    }
}

# 10. Desktop Shortcut
try {
    $commonDesktop = [Environment]::GetFolderPath("CommonDesktopDirectory")
    if ($commonDesktop -and (Test-Path $commonDesktop)) {
        $shortcutPath = Join-Path $commonDesktop "Camera Monitor.lnk"
        $wsh = New-Object -ComObject WScript.Shell
        $shortcut = $wsh.CreateShortcut($shortcutPath)
        $shortcut.TargetPath = "explorer.exe"
        $shortcut.Arguments = "http://127.0.0.1:$Port"
        $shortcut.Description = "Camera Monitor Administration Dashboard"
        $shortcut.Save()
        Write-Info "Created desktop shortcut at $shortcutPath"
    }
} catch {
    Write-Warning "Could not create public desktop shortcut: $_"
}

# 11. Start task and verify health
if (-not $SkipTaskStart) {
    Write-Info "Starting service task $TaskName..."
    Start-ScheduledTask -TaskName $TaskName

    Write-Info "Waiting for Camera Monitor to become healthy on port $Port..."
    $healthy = $false
    for ($i = 0; $i -lt 30; $i++) {
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
        Write-Pass "Camera Monitor installed and running successfully on http://127.0.0.1:$Port"
    } else {
        Write-Warning "Service started but health endpoint did not respond within 30s. Check logs at $HomePath\logs\camera-monitor.log"
    }
} else {
    Write-Pass "Installation complete. (Task startup skipped by parameter)"
}
