# Camera Monitor - Windows Uninstallation Script
# Requires PowerShell 5.1+, Windows 10/11 or Server 2016+ (64-bit)
# ASCII only

[CmdletBinding()]
param(
    [Alias("InstallDir")][string]$InstallPath = "C:\Program Files\CameraMonitor",
    [Alias("HomeDir")][string]$HomePath = "C:\ProgramData\CameraMonitor",
    [string]$TaskName = "CameraMonitor",
    [string]$BackupTaskName = "$TaskName Backup",
    [string]$RemoveData = "",
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
        Write-Host "[DRY-RUN] Notice: Script is running without elevation (Administrator required for live uninstall)."
    } else {
        Write-Error "Administrator privileges are required. Please run this script in an elevated PowerShell session (Run as administrator)."
        exit 1
    }
}

if ($DryRun) {
    Write-Host "============================================================"
    Write-Host "Camera Monitor - Uninstaller Dry Run Plan"
    Write-Host "============================================================"
    Write-Host "Target Install Path: $InstallPath"
    Write-Host "Target Home Path:    $HomePath (RemoveData: '$RemoveData')"
    Write-Host "Scheduled Tasks:     $TaskName, $BackupTaskName"
    $powerBeforeFile = Join-Path $HomePath "power-before.txt"
    if (Test-Path $powerBeforeFile) {
        $standby = 0
        $hibernate = 0
        $lines = Get-Content $powerBeforeFile -ErrorAction SilentlyContinue
        foreach ($line in $lines) {
            if ($line -match "STANDBY_TIMEOUT_AC=(\d+)") { $standby = [int]$matches[1] }
            if ($line -match "HIBERNATE_TIMEOUT_AC=(\d+)") { $hibernate = [int]$matches[1] }
        }
        Write-Host "Power Settings:      Would restore AC sleep ($standby min) and hibernate ($hibernate min) from $powerBeforeFile"
    } else {
        Write-Host "Power Settings:      No $powerBeforeFile found; leaving power settings unchanged."
    }
    Write-Host "============================================================"
    Write-Host "[DRY-RUN] Uninstaller plan validated successfully."
    exit 0
}

# 2. Stop and unregister tasks
foreach ($t in @($TaskName, $BackupTaskName)) {
    try {
        $task = Get-ScheduledTask -TaskName $t -ErrorAction SilentlyContinue
        if ($task) {
            Write-Info "Stopping scheduled task $t..."
            Stop-ScheduledTask -TaskName $t -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 1
            Write-Info "Unregistering scheduled task $t..."
            Unregister-ScheduledTask -TaskName $t -Confirm:$false -ErrorAction SilentlyContinue
        }
    } catch {
        Write-Warning "Failed while removing task $($t): $_"
    }
}

# 3. Terminate running processes originating from InstallPath
try {
    $procs = Get-Process -Name python -ErrorAction SilentlyContinue
    if ($procs) {
        foreach ($p in $procs) {
            try {
                if ($p.Path -and $p.Path.StartsWith($InstallPath, [System.StringComparison]::OrdinalIgnoreCase)) {
                    Write-Info "Terminating running process $($p.Id) from $InstallPath..."
                    Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
                }
            } catch {
                # continue
            }
        }
    }
} catch {
    # continue
}

# 4. Remove Desktop Shortcut
try {
    $commonDesktop = [Environment]::GetFolderPath("CommonDesktopDirectory")
    if ($commonDesktop) {
        $shortcutPath = Join-Path $commonDesktop "Camera Monitor.lnk"
        if (Test-Path $shortcutPath) {
            Remove-Item -Path $shortcutPath -Force -ErrorAction SilentlyContinue
            Write-Info "Removed desktop shortcut: $shortcutPath"
        }
    }
} catch {
    Write-Warning "Could not remove desktop shortcut: $_"
}

# 5. Restore Power Settings
$powerBeforeFile = Join-Path $HomePath "power-before.txt"
if (Test-Path $powerBeforeFile) {
    $standby = 0
    $hibernate = 0
    $hasStandby = $false
    $hasHibernate = $false
    $lines = Get-Content $powerBeforeFile -ErrorAction SilentlyContinue
    foreach ($line in $lines) {
        if ($line -match "STANDBY_TIMEOUT_AC=(\d+)") {
            $standby = [int]$matches[1]
            $hasStandby = $true
        }
        if ($line -match "HIBERNATE_TIMEOUT_AC=(\d+)") {
            $hibernate = [int]$matches[1]
            $hasHibernate = $true
        }
    }
    try {
        if ($hasStandby) {
            & powercfg /change standby-timeout-ac $standby
        }
        if ($hasHibernate) {
            & powercfg /change hibernate-timeout-ac $hibernate
        }
        Write-Info "Restored AC power settings from $powerBeforeFile (standby-timeout-ac=$standby min, hibernate-timeout-ac=$hibernate min)."
    } catch {
        Write-Warning "Could not restore power configuration: $_"
    }
} else {
    Write-Info "No power-before.txt found at $powerBeforeFile (or -SkipPowerSettings was used at install); leaving power policy unchanged."
}

# 6. Remove Program Files
if (Test-Path $InstallPath) {
    Write-Info "Removing program files at $InstallPath..."
    Remove-Item -Path $InstallPath -Recurse -Force -ErrorAction SilentlyContinue
}

$prevPath = "$InstallPath.previous"
if (Test-Path $prevPath) {
    Write-Info "Removing previous backup files at $prevPath..."
    Remove-Item -Path $prevPath -Recurse -Force -ErrorAction SilentlyContinue
}

# 6. Data removal policy
if ($RemoveData -eq "DELETE") {
    if (Test-Path $HomePath) {
        Write-Info "Removing data and configuration at $HomePath..."
        Remove-Item -Path $HomePath -Recurse -Force -ErrorAction SilentlyContinue
    }
    Write-Pass "Uninstallation complete. All program files and data removed."
} else {
    Write-Pass "Uninstallation complete. Program files removed."
    if (Test-Path $HomePath) {
        Write-Info "Preserved data and logs at: $HomePath"
        Write-Info "To permanently remove data, run: .\uninstall.cmd -RemoveData DELETE"
    }
}
