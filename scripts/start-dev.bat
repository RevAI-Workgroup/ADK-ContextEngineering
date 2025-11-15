@echo off
REM Development server startup script for Windows
REM Starts both backend and frontend, handles graceful shutdown

setlocal EnableDelayedExpansion

cd /d "%~dp0\.."

REM Initialize PID variables
set BACKEND_PID=
set FRONTEND_PID=
set PID_FILE=%TEMP%\adk-dev-pids.txt

REM Clean up any existing PID file
if exist "%PID_FILE%" del "%PID_FILE%" >nul 2>&1

REM Jump to main execution
goto :main

:cleanup
REM Cleanup function to kill processes by PID
REM The /T flag in taskkill automatically kills child processes (process tree)
echo.
echo [CLEANUP] Stopping development servers...

REM Try to read PIDs from file if variables are not set
if not defined BACKEND_PID if not defined FRONTEND_PID (
    if exist "%PID_FILE%" (
        for /f "tokens=1,2" %%a in ('type "%PID_FILE%"') do (
            if "%%a"=="BACKEND" set BACKEND_PID=%%b
            if "%%a"=="FRONTEND" set FRONTEND_PID=%%b
        )
    )
)

if defined BACKEND_PID (
    echo [CLEANUP] Stopping backend (PID: !BACKEND_PID!)...
    taskkill /PID !BACKEND_PID! /F /T >nul 2>&1
    if errorlevel 1 (
        REM PID might not exist anymore, try window title as fallback
        taskkill /FI "WindowTitle eq ADK-Backend*" /F /T >nul 2>&1
    )
) else (
    REM No PID captured, use window title fallback
    echo [CLEANUP] Stopping backend (using window title fallback)...
    taskkill /FI "WindowTitle eq ADK-Backend*" /F /T >nul 2>&1
)

if defined FRONTEND_PID (
    echo [CLEANUP] Stopping frontend (PID: !FRONTEND_PID!)...
    taskkill /PID !FRONTEND_PID! /F /T >nul 2>&1
    if errorlevel 1 (
        REM PID might not exist anymore, try window title as fallback
        taskkill /FI "WindowTitle eq ADK-Frontend*" /F /T >nul 2>&1
    )
) else (
    REM No PID captured, use window title fallback
    echo [CLEANUP] Stopping frontend (using window title fallback)...
    taskkill /FI "WindowTitle eq ADK-Frontend*" /F /T >nul 2>&1
)

echo [SYSTEM] All servers stopped
REM Clean up PID file
if exist "%PID_FILE%" del "%PID_FILE%" >nul 2>&1
exit /b 0

:main
echo.
echo ═══════════════════════════════════════════
echo    ADK Context Engineering - Dev Server
echo ═══════════════════════════════════════════
echo.

echo [SYSTEM] Platform: Windows
echo [SYSTEM] Starting development servers...
echo.

REM Check if venv exists
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found!
    echo [ERROR] Please run: python -m venv venv
    echo [ERROR] Then: venv\Scripts\activate ^&^& pip install -r requirements.txt
    exit /b 1
)

REM Validate frontend setup
if not exist "frontend" (
    echo [ERROR] Frontend directory not found!
    exit /b 1
)

where pnpm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pnpm not found! Please install: npm install -g pnpm
    exit /b 1
)

REM Start backend in a new window and capture PID
echo [BACKEND] Starting FastAPI server...
start "ADK-Backend" /min cmd /c "venv\Scripts\activate && set PYTHONPATH=%cd% && uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000"

REM Give backend a moment to start, then capture PID
REM Wait a bit longer to ensure uvicorn process is actually running
timeout /t 3 /nobreak >nul

REM Capture backend PID by finding the uvicorn process
REM Use wmic to find process with uvicorn in command line (most reliable)
for /f "skip=1 tokens=2 delims=," %%a in ('wmic process where "CommandLine like '%%uvicorn%%' and CommandLine like '%%src.api.main%%'" get ProcessId /format:csv 2^>nul') do (
    if not "%%a"=="" (
        set BACKEND_PID=%%a
        goto :backend_pid_found
    )
)

REM Fallback: try to find any uvicorn process
for /f "skip=1 tokens=2 delims=," %%a in ('wmic process where "CommandLine like '%%uvicorn%%'" get ProcessId /format:csv 2^>nul') do (
    if not "%%a"=="" (
        set BACKEND_PID=%%a
        goto :backend_pid_found
    )
)

REM Fallback: try to find by window title using tasklist
for /f "tokens=2" %%a in ('tasklist /FI "WindowTitle eq ADK-Backend*" /FO CSV /NH 2^>nul') do (
    set "BACKEND_PID=%%~a"
    if not "!BACKEND_PID!"=="" goto :backend_pid_found
)

:backend_pid_found
if defined BACKEND_PID (
    echo [BACKEND] Started with PID: !BACKEND_PID!
    REM Save PID to file for cleanup script
    echo BACKEND !BACKEND_PID!>> "%PID_FILE%"
) else (
    echo [WARNING] Could not capture backend PID, will use fallback cleanup method
)

REM Start frontend in a new window and capture PID
echo [FRONTEND] Starting Vite dev server...
start "ADK-Frontend" /min cmd /c "cd frontend && pnpm dev"

REM Give frontend a moment to start, then capture PID
REM Wait a bit longer to ensure pnpm/vite process is actually running
timeout /t 3 /nobreak >nul

REM Capture frontend PID by finding the pnpm/vite process
REM Look for pnpm process running in frontend directory (most reliable)
for /f "tokens=*" %%a in ('powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*pnpm*' -and $_.CommandLine -like '*frontend*' } | Select-Object -First 1 -ExpandProperty ProcessId" 2^>nul') do (
    if not "%%a"=="" (
        set FRONTEND_PID=%%a
        goto :frontend_pid_found
    )
)

REM Fallback: try to find vite process (pnpm spawns vite)
for /f "tokens=*" %%a in ('powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*vite*' } | Select-Object -First 1 -ExpandProperty ProcessId" 2^>nul') do (
    if not "%%a"=="" (
        set FRONTEND_PID=%%a
        goto :frontend_pid_found
    )
)

REM Fallback: try to find any pnpm process
for /f "tokens=*" %%a in ('powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*pnpm*' } | Select-Object -First 1 -ExpandProperty ProcessId" 2^>nul') do (
    if not "%%a"=="" (
        set FRONTEND_PID=%%a
        goto :frontend_pid_found
    )
)

REM Fallback: try to find by window title using PowerShell
for /f "tokens=*" %%a in ('powershell -Command "Get-Process | Where-Object { $_.MainWindowTitle -like 'ADK-Frontend*' } | Select-Object -First 1 -ExpandProperty Id" 2^>nul') do (
    set "FRONTEND_PID=%%a"
    if not "!FRONTEND_PID!"=="" goto :frontend_pid_found
)

:frontend_pid_found
if defined FRONTEND_PID (
    echo [FRONTEND] Started with PID: !FRONTEND_PID!
    REM Save PID to file for cleanup script
    echo FRONTEND !FRONTEND_PID!>> "%PID_FILE%"
) else (
    echo [WARNING] Could not capture frontend PID, will use fallback cleanup method
)

echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo [SYSTEM] ✨ Development servers are running!
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo [BACKEND] http://localhost:8000 (API)
echo [BACKEND] http://localhost:8000/docs (API Docs)
echo [FRONTEND] http://localhost:5173 (UI)
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo [SYSTEM] Press any key to stop all servers cleanly
echo [SYSTEM] NOTE: If you press Ctrl+C, run stop-dev.bat to clean up
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

REM Keep window open until user closes it or presses a key
REM IMPORTANT: Ctrl+C will NOT trigger cleanup in batch scripts
REM Use pause which waits for any key (not Ctrl+C)
echo Press any key to stop all servers...
pause >nul 2>&1

REM Cleanup will be called on normal exit
REM Clean up PID file
if exist "%PID_FILE%" del "%PID_FILE%" >nul 2>&1
goto :cleanup

