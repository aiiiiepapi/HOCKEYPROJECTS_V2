@echo off
REM ============================================================
REM  HOCKEYPROJECTS V2 - DEL (PENNY DEL) raw data lake fetcher
REM
REM  RUN THE STEPS IN ORDER. Step 3 prints the projected lake size -
REM  send that to the Manager and WAIT before running step 4.
REM
REM    1. FETCH_DEL_LAKE.bat schedule    (fixture lists per season)
REM    2. FETCH_DEL_LAKE.bat reconcile   (0/0 both directions)
REM    3. FETCH_DEL_LAKE.bat sample      (SIZE PROJECTION - stop here)
REM    4. FETCH_DEL_LAKE.bat full        (builds the lake; hours)
REM    5. FETCH_DEL_LAKE.bat verify      (re-hash AFTER transfer)
REM
REM  Safe to stop and re-run: downloaded files are skipped.
REM  Output: tools\del_lake\
REM ============================================================
where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found. Install it from https://www.python.org/downloads/
    echo IMPORTANT: tick "Add python.exe to PATH" during install, then re-run this file.
    pause
    exit /b 1
)
if "%~1"=="" (
    echo Tell it which step to run, for example:
    echo     FETCH_DEL_LAKE.bat schedule
    echo Steps: schedule ^| reconcile ^| sample ^| full ^| verify
    pause
    exit /b 1
)
if /I "%~1"=="schedule"  python "%~dp0fetch_del_raw.py" --schedule
if /I "%~1"=="reconcile" python "%~dp0fetch_del_raw.py" --reconcile
if /I "%~1"=="sample"    python "%~dp0fetch_del_raw.py" --sample 10
if /I "%~1"=="full"      python "%~dp0fetch_del_raw.py" --full
if /I "%~1"=="verify"    python "%~dp0fetch_del_raw.py" --verify
echo.
echo Finished. You can close this window.
pause
