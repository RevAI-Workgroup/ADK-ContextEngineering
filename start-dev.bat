@echo off
REM Development server startup script for Windows
REM Starts both backend and frontend, handles graceful shutdown

setlocal EnableDelayedExpansion

cd /d "%~dp0"

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

REM Start backend in a new window
echo [BACKEND] Starting FastAPI server...
start "ADK-Backend" /min cmd /c "venv\Scripts\activate && set PYTHONPATH=%cd% && uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000"

REM Give backend a moment to start
timeout /t 3 /nobreak >nul

REM Start frontend in a new window
echo [FRONTEND] Starting Vite dev server...
start "ADK-Frontend" /min cmd /c "cd frontend && pnpm dev"

REM Wait a moment for both to initialize
timeout /t 2 /nobreak >nul

echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo [SYSTEM] ✨ Development servers are running!
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo [BACKEND] http://localhost:8000 (API)
echo [BACKEND] http://localhost:8000/docs (API Docs)
echo [FRONTEND] http://localhost:5173 (UI)
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo [SYSTEM] Close this window to stop all servers
echo.

REM Keep window open until user closes it
echo Press any key to stop all servers...
pause >nul

REM Kill backend and frontend
taskkill /FI "WindowTitle eq ADK-Backend*" /F /T >nul 2>&1
taskkill /FI "WindowTitle eq ADK-Frontend*" /F /T >nul 2>&1

echo [SYSTEM] All servers stopped

