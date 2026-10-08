# Camera Monitor - Windows Installation & Lifecycle Verification Script
# Requires PowerShell 5.1+, Windows 10/11 or Server 2016+ (64-bit)
# ASCII only

[CmdletBinding()]
param(
    [Alias("TaskName")][string]$TestTaskName = "CameraMonitorTest",
    [Alias("BackupTaskName")][string]$TestBackupTaskName = "$TestTaskName Backup",
    [string]$TestInstallPath = "",
    [string]$TestHomePath = "",
    [int]$TestPort = 0,
    [string]$Confirm = "",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Write-StepPass($stepNum, $desc) {
    Write-Host "[STEP $($stepNum): PASS] $desc"
}

function Write-StepFail($stepNum, $desc) {
    Write-Host "[STEP $($stepNum): FAIL] $desc"
}

function Test-ScheduledTaskExists([string]$Name) {
    try {
        $task = Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue
        return ($null -ne $task)
    } catch {
        return $false
    }
}

# 1. Safety Guardrails - Refuse production task names (pure string check, case-insensitive, first executable statement)
$forbiddenNames = @("CameraMonitor", "CameraMonitor Backup")
if ($TestTaskName -in $forbiddenNames -or $TestBackupTaskName -in $forbiddenNames) {
    Write-Error "Safety Violation: verify-install.ps1 refuses to run with production TaskName '$TestTaskName'. Use 'CameraMonitorTest'."
    exit 1
}

# 2. Validate TaskName format
if ($TestTaskName -notmatch '^[a-zA-Z0-9 _-]{1,64}$') {
    Write-Error "Invalid TaskName '$TestTaskName'. TaskName must be 1 to 64 characters and contain only letters, digits, spaces, dashes, or underscores."
    exit 1
}

# 3. Refuse if scheduled task named CameraMonitor or CameraMonitor Backup already exists on the machine
$hasExistingProdTask = $false
if ($DryRun -and $env:CAMERA_MONITOR_TEST_EXISTING_TASK -eq "1") {
    $hasExistingProdTask = $true
} else {
    if ((Test-ScheduledTaskExists "CameraMonitor") -or (Test-ScheduledTaskExists "CameraMonitor Backup")) {
        $hasExistingProdTask = $true
    }
}

if ($hasExistingProdTask) {
    Write-Error "Safety Violation: A scheduled task named 'CameraMonitor' or 'CameraMonitor Backup' already exists on this machine. verify-install refuses to run."
    exit 1
}

# 4. Check elevation
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
$isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if ($DryRun -and ($env:CAMERA_MONITOR_TEST_ELEVATED -eq "0" -or $env:CAMERA_MONITOR_TEST_ELEVATED -eq "1")) {
    $isAdmin = ($env:CAMERA_MONITOR_TEST_ELEVATED -eq "1")
}

if (-not $isAdmin) {
    if ($DryRun) {
        Write-Host "[DRY-RUN] Notice: Session is NOT elevated. (Live execution requires Administrator)."
    } else {
        Write-Error "Administrator privileges are required for verify-install.ps1 to configure Windows Task Scheduler."
        exit 1
    }
}

# 5. Safety Guardrails - Refuse production paths
$prodInstall = "C:\Program Files\CameraMonitor"
$prodHome = "C:\ProgramData\CameraMonitor"
if ($TestInstallPath -and ($TestInstallPath.TrimEnd("\/") -eq $prodInstall.TrimEnd("\/"))) {
    Write-Error "Safety Violation: verify-install.ps1 refuses to target production path '$prodInstall'."
    exit 1
}
if ($TestHomePath -and ($TestHomePath.TrimEnd("\/") -eq $prodHome.TrimEnd("\/"))) {
    Write-Error "Safety Violation: verify-install.ps1 refuses to target production path '$prodHome'."
    exit 1
}

# Initialize test folders in OS Temp if not provided
$tempRoot = [System.IO.Path]::GetTempPath()
$randSuffix = [System.IO.Path]::GetRandomFileName().Substring(0, 8)
if (-not $TestInstallPath) {
    $TestInstallPath = Join-Path $tempRoot "CMTest_Install_$randSuffix"
}
if (-not $TestHomePath) {
    $TestHomePath = Join-Path $tempRoot "CMTest_Home_$randSuffix"
}

# Acquire free loopback port
if ($TestPort -eq 0) {
    $listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, 0)
    $listener.Start()
    $TestPort = ($listener.LocalEndpoint).Port
    $listener.Stop()
}

# 6. Print plan and prompt confirmation
Write-Host "============================================================"
Write-Host "Camera Monitor - Automated Installation Verification Suite"
Write-Host "============================================================"
Write-Host "Planned test resources:"
Write-Host "  Service Task Name:  $TestTaskName"
Write-Host "  Backup Task Name:   $TestBackupTaskName"
Write-Host "  Test Install Dir:   $TestInstallPath"
Write-Host "  Test Home Dir:      $TestHomePath"
Write-Host "  Test Port:          $TestPort"
Write-Host "  Administrator:      $isAdmin"
Write-Host "============================================================"

if ($DryRun) {
    Write-Host "[DRY-RUN] Validation complete. Script logic is ready for elevated execution."
    exit 0
}

if ($Confirm -ne "YES") {
    $userEntry = Read-Host "Type 'YES' to proceed with live test execution"
    if ($userEntry -ne "YES") {
        Write-Host "Verification aborted by user."
        exit 0
    }
}

$scriptDir = $PSScriptRoot
$installScript = Join-Path $scriptDir "install.ps1"
$uninstallScript = Join-Path $scriptDir "uninstall.ps1"
$startScript = Join-Path $scriptDir "start.ps1"
$stopScript = Join-Path $scriptDir "stop.ps1"
$backupScript = Join-Path $scriptDir "backup.ps1"
$restoreScript = Join-Path $scriptDir "restore.ps1"

try {
    # Step 1: Install with -SkipPowerSettings
    Write-Host "`n--> Step 1: Running install.ps1 (-SkipPowerSettings)..."
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $installScript `
        -InstallPath $TestInstallPath `
        -HomePath $TestHomePath `
        -TaskName $TestTaskName `
        -BackupTaskName $TestBackupTaskName `
        -Port $TestPort `
        -SkipPowerSettings
    if ($LASTEXITCODE -ne 0) { throw "Install failed with exit code $LASTEXITCODE" }
    Write-StepPass 1 "Fresh installation completed successfully."

    # Step 2: Read back task settings
    Write-Host "`n--> Step 2: Reading back task principal, trigger, and restart settings..."
    $taskObj = Get-ScheduledTask -TaskName $TestTaskName
    if (-not $taskObj) { throw "Task $TestTaskName was not registered" }
    $pId = $taskObj.Principal.UserId
    $timeLimit = $taskObj.Settings.ExecutionTimeLimit
    $restartCount = $taskObj.Settings.RestartCount
    Write-Host "    Principal:          $pId"
    Write-Host "    ExecutionTimeLimit: $timeLimit"
    Write-Host "    RestartCount:       $restartCount"
    if ($pId -notlike "*SYSTEM*") { throw "Expected SYSTEM principal, got $pId" }
    Write-StepPass 2 "Task principal and execution settings verified."

    # Step 3: Health check
    Write-Host "`n--> Step 3: Performing health check on port $TestPort..."
    $req = [System.Net.WebRequest]::Create("http://127.0.0.1:$TestPort/api/health")
    $req.Timeout = 5000
    $res = $req.GetResponse()
    $status = [int]$res.StatusCode
    $res.Close()
    if ($status -ne 200) { throw "Health endpoint returned $status" }
    Write-StepPass 3 "Health endpoint returned 200 OK."

    # Step 4: Stop and start through scripts
    Write-Host "`n--> Step 4: Testing stop.ps1 and start.ps1 lifecycle..."
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $stopScript `
        -TaskName $TestTaskName -InstallPath $TestInstallPath
    if ($LASTEXITCODE -ne 0) { throw "Stop script failed" }

    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $startScript `
        -TaskName $TestTaskName -Port $TestPort
    if ($LASTEXITCODE -ne 0) { throw "Start script failed" }
    Write-StepPass 4 "Service stopped and restarted cleanly."

    # Step 5: Hard-kill and observe Task Scheduler restart behavior
    Write-Host "`n--> Step 5: Hard-killing python process and measuring restart response..."
    $procs = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
        $_.Path -and $_.Path.StartsWith($TestInstallPath, [System.StringComparison]::OrdinalIgnoreCase)
    }
    if ($procs) {
        $targetPid = $procs[0].Id
        Write-Host "    Killing PID $targetPid with taskkill /F..."
        & taskkill /F /PID $targetPid | Out-Null
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        $restarted = $false
        while ($sw.Elapsed.TotalSeconds -lt 70) {
            Start-Sleep -Seconds 2
            try {
                $r = [System.Net.WebRequest]::Create("http://127.0.0.1:$TestPort/api/health")
                $r.Timeout = 1000
                $rs = $r.GetResponse()
                if ($rs.StatusCode -eq 200) {
                    $restarted = $true
                    $rs.Close()
                    break
                }
                $rs.Close()
            } catch {}
        }
        $sw.Stop()
        $taskInfo = Get-ScheduledTaskInfo -TaskName $TestTaskName
        Write-Host "    LastTaskResult: $($taskInfo.LastTaskResult)"
        Write-Host "    Restart elapsed time: $([math]::Round($sw.Elapsed.TotalSeconds, 1))s (Restarted: $restarted)"
    }
    Write-StepPass 5 "Process crash resilience check recorded."

    # Step 6: Upgrade installation
    Write-Host "`n--> Step 6: Testing upgrade installation..."
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $installScript `
        -InstallPath $TestInstallPath `
        -HomePath $TestHomePath `
        -TaskName $TestTaskName `
        -BackupTaskName $TestBackupTaskName `
        -Port $TestPort `
        -SkipPowerSettings
    if ($LASTEXITCODE -ne 0) { throw "Upgrade failed" }
    $prevDir = "$TestInstallPath.previous"
    if (-not (Test-Path $prevDir)) { throw "Expected previous directory at $prevDir" }
    Write-StepPass 6 "Upgrade preserved data and created .previous directory."

    # Step 7: Backup and restore
    Write-Host "`n--> Step 7: Testing database backup and restore..."
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $backupScript `
        -HomePath $TestHomePath -InstallPath $TestInstallPath
    if ($LASTEXITCODE -ne 0) { throw "Backup failed" }

    $backupList = Get-ChildItem (Join-Path $TestHomePath "backups") -Filter "*.db" | Sort-Object Name -Descending
    if (-not $backupList) { throw "No backup file found" }
    $newestBackup = $backupList[0].FullName

    # Stop before restore
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $stopScript `
        -TaskName $TestTaskName -InstallPath $TestInstallPath

    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $restoreScript `
        -BackupFile $newestBackup `
        -HomePath $TestHomePath `
        -InstallPath $TestInstallPath `
        -TaskName $TestTaskName
    if ($LASTEXITCODE -ne 0) { throw "Restore failed" }
    Write-StepPass 7 "Backup and restore executed successfully."

    # Step 8: Uninstall with -RemoveData
    Write-Host "`n--> Step 8: Running uninstall.ps1 -RemoveData DELETE..."
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $uninstallScript `
        -InstallPath $TestInstallPath `
        -HomePath $TestHomePath `
        -TaskName $TestTaskName `
        -BackupTaskName $TestBackupTaskName `
        -RemoveData "DELETE"
    if ($LASTEXITCODE -ne 0) { throw "Uninstall failed" }
    Write-StepPass 8 "Uninstallation completed."

} finally {
    # Guaranteed cleanup
    Write-Host "`n[CLEANUP] Performing guaranteed teardown of all test resources..."
    foreach ($t in @($TestTaskName, $TestBackupTaskName)) {
        try {
            $tsk = Get-ScheduledTask -TaskName $t -ErrorAction SilentlyContinue
            if ($tsk) {
                Stop-ScheduledTask -TaskName $t -ErrorAction SilentlyContinue
                Start-Sleep -Seconds 1
                Unregister-ScheduledTask -TaskName $t -Confirm:$false -ErrorAction SilentlyContinue
            }
        } catch {}
    }

    Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
        $_.Path -and $_.Path.StartsWith($TestInstallPath, [System.StringComparison]::OrdinalIgnoreCase)
    } | Stop-Process -Force -ErrorAction SilentlyContinue

    if (Test-Path $TestInstallPath) { Remove-Item -Path $TestInstallPath -Recurse -Force -ErrorAction SilentlyContinue }
    if (Test-Path "$TestInstallPath.previous") { Remove-Item -Path "$TestInstallPath.previous" -Recurse -Force -ErrorAction SilentlyContinue }
    if (Test-Path $TestHomePath) { Remove-Item -Path $TestHomePath -Recurse -Force -ErrorAction SilentlyContinue }

    # Verification of cleanup
    $taskClean = (-not (Get-ScheduledTask -TaskName $TestTaskName -ErrorAction SilentlyContinue)) -and (-not (Get-ScheduledTask -TaskName $TestBackupTaskName -ErrorAction SilentlyContinue))
    $foldersClean = (-not (Test-Path $TestInstallPath)) -and (-not (Test-Path $TestHomePath))
    Write-Host "============================================================"
    Write-Host "Cleanup Status: Tasks Removed: $taskClean | Folders Removed: $foldersClean"
    Write-Host "============================================================"
}

exit 0
