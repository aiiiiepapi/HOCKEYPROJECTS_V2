@echo off
REM ============================================================
REM  HOCKEYPROJECTS V2 - Mestis raw data lake fetcher
REM  Double-click to run. Safe to stop and re-run any time
REM  (already-downloaded pages are skipped automatically).
REM  4 seasons x ~250-450 games x 3 HTML pages + ICS schedules.
REM  Expect roughly 30-60 minutes on the first run.
REM  Output: C:\dev\HOCKEYPROJECTS_V2\data\raw\mestis
REM  When it finishes it prints per-season counts - paste the
REM  whole output back to the Mestis scraping session.
REM ============================================================
where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found. Install it from https://www.python.org/downloads/
    echo IMPORTANT: tick "Add python.exe to PATH" during install, then re-run this file.
    pause
    exit /b 1
)
python "%~dp0fetch_mestis.py" %*
echo.
echo Now running the lake verification report...
python "%~dp0verify_mestis_lake.py" --lake "C:\dev\HOCKEYPROJECTS_V2\data\raw\mestis"
echo.
echo Finished. Paste EVERYTHING above back to the Mestis session.
pause
