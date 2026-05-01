@echo off
REM Non-interactive trigger for intranet-post-runner.
REM
REM Same as run.bat but designed for Windows Task Scheduler:
REM   - no `pause` (would hang the scheduled task forever)
REM   - no echo to console (scheduler runs headless)
REM   - exit code propagates so Task Scheduler History shows pass/fail
REM
REM Manual runs should still use run.bat — it tails the log so you can see
REM what just happened.

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: .venv not found 1>&2
    exit /b 1
)

.venv\Scripts\python.exe intranet_post.py
exit /b %errorlevel%
