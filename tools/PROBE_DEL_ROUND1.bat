@echo off
REM ============================================================
REM  HOCKEYPROJECTS V2 - DEL (PENNY DEL) ROUND 1 CAPABILITY PROBE
REM
REM  Double-click to run. This DOWNLOADS NOTHING AT SCALE - it grabs
REM  a handful of pages and saves them verbatim so we can answer one
REM  question: does the DEL source show WHEN a goalie was pulled?
REM
REM  Takes about a minute. Safe to re-run (already-downloaded files
REM  are skipped). Output: tools\del_probe\
REM
REM  When it finishes, send back the whole tools\del_probe\ folder.
REM ============================================================
where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found. Install it from https://www.python.org/downloads/
    echo IMPORTANT: tick "Add python.exe to PATH" during install, then re-run this file.
    pause
    exit /b 1
)
python "%~dp0del_round1_probe.py" %*
echo.
echo Finished. Send back the tools\del_probe\ folder.
pause
