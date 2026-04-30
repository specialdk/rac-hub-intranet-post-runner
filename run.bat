@echo off
REM Manual trigger for intranet-post-runner.
REM Double-click this from File Explorer to run the runner ad-hoc.
REM
REM Same script Task Scheduler will run hourly once configured — no
REM difference in behaviour or state, so you can run this any time.
REM On exit the window pauses so you can read the output; close it
REM with the X or by pressing a key.

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: .venv not found. Run setup from README.md first:
    echo   python -m venv .venv
    echo   .venv\Scripts\activate
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)

echo === intranet-post run started at %date% %time% ===
echo.

.venv\Scripts\python.exe intranet_post.py
set EXITCODE=%errorlevel%

echo.
echo === run finished (exit code %EXITCODE%) ===
echo.
echo Last 20 log lines:
echo ----------------------------------------------------------
for /f "tokens=*" %%i in ('dir /b /od logs\*.log 2^>nul') do set LATEST=%%i
if defined LATEST (
    powershell -NoProfile -Command "Get-Content 'logs\%LATEST%' -Tail 20"
) else (
    echo (no log file yet)
)
echo ----------------------------------------------------------
echo.
pause
exit /b %EXITCODE%
