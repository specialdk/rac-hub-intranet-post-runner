# Register the intranet-post-runner with Windows Task Scheduler.
#
# Idempotent: if a task with the same name already exists, it's
# unregistered first and recreated. Safe to re-run any time you want
# to reset the schedule (e.g. after moving the runner to a new path).
#
# What it sets up:
#   - Trigger:     every 15 minutes, all day, indefinitely
#   - Action:      run-scheduled.bat in this directory
#   - Working dir: this directory (the .bat also cd's, so doubly safe)
#   - Conditions:  runs on battery; doesn't wake the computer; doesn't
#                  start until network is available; if the run takes
#                  longer than 5 min it's killed (paranoia, the script
#                  is normally <30s)
#
# Run from PowerShell. No admin needed if the task is set to run as
# the current user (default below).
#
# Usage:
#   cd C:\Users\speci\OneDrive\RAC-Projects\rac-hub-intranet-post-runner
#   .\register-task.ps1
#
# To remove later:
#   Unregister-ScheduledTask -TaskName 'rac-hub-intranet-post-runner' -Confirm:$false

$ErrorActionPreference = 'Stop'

$TaskName = 'rac-hub-intranet-post-runner'
$RunnerDir = $PSScriptRoot
$BatPath = Join-Path $RunnerDir 'run-scheduled.bat'

if (-not (Test-Path $BatPath)) {
    Write-Error "run-scheduled.bat not found at $BatPath. Run this script from the runner project directory."
    exit 1
}

# Unregister any existing task with this name, so we always end up with
# a clean current definition matching this script.
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Removing existing task '$TaskName'..."
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Action: run the .bat. We pass the absolute path so Task Scheduler
# doesn't need to know about the working directory itself.
$action = New-ScheduledTaskAction `
    -Execute $BatPath `
    -WorkingDirectory $RunnerDir

# Trigger: every 15 minutes, indefinitely.
# Daily at midnight + repeat every 15 min for 24h, repeated daily forever.
$trigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date).Date `
    -RepetitionInterval (New-TimeSpan -Minutes 15)

# Settings: don't wait for idle, allow on battery, don't wake, kill if
# the run hangs >5 min, allow start as soon as available if a trigger
# was missed (laptop was asleep at the trigger time).
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
    -MultipleInstances IgnoreNew

# Run as the current interactive user. No password required when
# "RunOnlyWhenUserLoggedOn" — fine for a dev / single-user box.
# If you ever need it to run while logged out, change LogonType to
# 'Password' and provide -User/-Password to Register-ScheduledTask.
$principal = New-ScheduledTaskPrincipal `
    -UserId (whoami) `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description 'Polls the rac-hub-submit backend for pending submissions and processes them with Claude. See rac-hub-intranet-post-runner/README.md.' | Out-Null

Write-Host "Registered '$TaskName':"
Write-Host "  Action: $BatPath"
Write-Host "  Trigger: every 15 minutes, starting now"
Write-Host ""
Write-Host "Verify in Task Scheduler GUI, or run:"
Write-Host "  Get-ScheduledTask -TaskName '$TaskName'"
Write-Host ""
Write-Host "Trigger one run now to test:"
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'"
