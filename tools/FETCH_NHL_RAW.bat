@echo off
REM ============================================================
REM  HOCKEYPROJECTS V2 - NHL raw data lake fetcher
REM  Double-click to run. Safe to stop and re-run any time
REM  (already-downloaded games are skipped automatically).
REM  Expect roughly 2600+ games x 2 files; allow it to run for
REM  a few hours the first time. Output: C:\dev\HOCKEYPROJECTS_V2\data\raw\nhl
REM ============================================================
where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found. Install it from https://www.python.org/downloads/
    echo IMPORTANT: tick "Add python.exe to PATH" during install, then re-run this file.
    pause
    exit /b 1
)
python "%~dp0fetch_nhl_raw.py" %*
echo.
echo Finished. You can close this window.
pause
