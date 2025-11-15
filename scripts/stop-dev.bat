@echo off
REM Development server cleanup script for Windows
REM Stops backend and frontend servers by PID or process name
REM Can be run independently to clean up orphan processes

setlocal EnableDelayedExpansion

cd /d "%~dp0\.."

echo.
echo ═══════════════════════════════════════════
echo    ADK Context Engineering - Stop Servers
echo ═══════════════════════════════════════════
echo.

set PID_FILE=%TEMP%\adk-dev-pids.txt
set BACKEND_PID=
set FRONTEND_PID=

REM Try to read PIDs from file if it exists
if exist "%PID_FILE%" (
    echo [SYSTEM] Reading PIDs from file...
    for /f "tokens=1,2" %%a in ('type "%PID_FILE%"') do (
        if "%%a"=="BACKEND" set BACKEND_PID=%%b
        if "%%a"=="FRONTEND" set FRONTEND_PID=%%b
    )
    del "%PID_FILE%" >nul 2>&1
)

echo [CLEANUP] Stopping development servers...

REM Stop backend
if defined BACKEND_PID (
    echo [CLEANUP] Stopping backend (PID: !BACKEND_PID!)...
    taskkill /PID !BACKEND_PID! /F /T >nul 2>&1
    if errorlevel 1 (
        echo [CLEANUP] PID not found, trying window title fallback...
        taskkill /FI "WindowTitle eq ADK-Backend*" /F /T >nul 2>&1
    )
) else (
    echo [CLEANUP] Stopping backend (using window title fallback)...
    taskkill /FI "WindowTitle eq ADK-Backend*" /F /T >nul 2>&1
)

REM Also kill any uvicorn processes on port 8000
for /f "tokens=*" %%a in ('powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess | Select-Object -Unique" 2^>nul') do (
    if not "%%a"=="" (
        echo [CLEANUP] Stopping process on port 8000 (PID: %%a)...
        taskkill /PID %%a /F /T >nul 2>&1
    )
)

REM Stop frontend
if defined FRONTEND_PID (
    echo [CLEANUP] Stopping frontend (PID: !FRONTEND_PID!)...
    taskkill /PID !FRONTEND_PID! /F /T >nul 2>&1
    if errorlevel 1 (
        echo [CLEANUP] PID not found, trying window title fallback...
        taskkill /FI "WindowTitle eq ADK-Frontend*" /F /T >nul 2>&1
    )
) else (
    echo [CLEANUP] Stopping frontend (using window title fallback)...
    taskkill /FI "WindowTitle eq ADK-Frontend*" /F /T >nul 2>&1
)

REM Also kill any vite/node processes on port 5173
for /f "tokens=*" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do (
    set "line=%%a"
    set "PID="
    for %%b in (!line!) do set "PID=%%b"
    if defined PID (
        echo [CLEANUP] Stopping process on port 5173 (PID: !PID!)...
        taskkill /PID !PID! /F /T >nul 2>&1
    )
)

REM Final cleanup: kill any remaining uvicorn processes
for /f "skip=1 tokens=2 delims=," %%a in ('wmic process where "CommandLine like '%%uvicorn%%' and CommandLine like '%%src.api.main%%'" get ProcessId /format:csv 2^>nul') do (
    if not "%%a"=="" (
        echo [CLEANUP] Stopping remaining uvicorn process (PID: %%a)...
        taskkill /PID %%a /F /T >nul 2>&1
    )
)

REM Final cleanup: kill any remaining vite processes
echo [CLEANUP] Stopping remaining vite process...
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*vite*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1

echo.
echo [SYSTEM] All servers stopped
echo.
pause

