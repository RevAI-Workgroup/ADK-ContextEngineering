#!/usr/bin/env pwsh
# Development server startup script for Windows (PowerShell)
# Starts both backend and frontend, handles graceful shutdown

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# Store job IDs for cleanup
$BackendJob = $null
$FrontendJob = $null

# Track exit code - only exit happens in Cleanup function
$Script:ExitCode = 0

function Write-Log {
    param(
        [string]$Prefix,
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host "[$Prefix] " -ForegroundColor $Color -NoNewline
    Write-Host $Message
}

function Cleanup {
    Write-Log "SYSTEM" "Shutting down servers..." "Yellow"
    
    if ($BackendJob) {
        Stop-Job -Job $BackendJob -ErrorAction SilentlyContinue
        Remove-Job -Job $BackendJob -ErrorAction SilentlyContinue
    }
    
    if ($FrontendJob) {
        Stop-Job -Job $FrontendJob -ErrorAction SilentlyContinue
        Remove-Job -Job $FrontendJob -ErrorAction SilentlyContinue
    }
    
    # Kill any remaining uvicorn or vite processes
    Get-Process -Name "uvicorn" -ErrorAction SilentlyContinue | Stop-Process -Force
    Get-Process | Where-Object { $_.CommandLine -like "*vite*" } -ErrorAction SilentlyContinue | Stop-Process -Force
    
    Write-Log "SYSTEM" "All servers stopped" "Yellow"
    exit $Script:ExitCode
}

# Set up cleanup on exit
Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action { Cleanup }

# Print header
Write-Host ""
Write-Host "╔═══════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   ADK Context Engineering - Dev Server   ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

Write-Log "SYSTEM" "Platform: Windows (PowerShell $($PSVersionTable.PSVersion))" "Cyan"
Write-Log "SYSTEM" "Starting development servers..." "Cyan"
Write-Host ""

# Check if venv exists
if (-not (Test-Path "venv\Scripts\Activate.ps1")) {
    Write-Log "ERROR" "Virtual environment not found!" "Red"
    Write-Log "ERROR" "Please run: python -m venv venv" "Red"
    Write-Log "ERROR" "Then: .\venv\Scripts\Activate.ps1; pip install -r requirements.txt" "Red"
    $Script:ExitCode = 1
    Cleanup
}

try {
    # Start backend
    Write-Log "BACKEND" "Starting FastAPI server..." "Blue"
    $BackendJob = Start-Job -ScriptBlock {
        Set-Location $using:PSScriptRoot
        & .\venv\Scripts\Activate.ps1
        $env:PYTHONPATH = $using:PSScriptRoot
        & uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
    }

    # Give backend a moment to start
    Start-Sleep -Seconds 2

    # Start frontend
    Write-Log "FRONTEND" "Starting Vite dev server..." "Green"
    $FrontendJob = Start-Job -ScriptBlock {
        Set-Location "$using:PSScriptRoot\frontend"
        & pnpm dev
    }

    # Wait a moment for both to initialize
    Start-Sleep -Seconds 2

    # Print status
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Log "SYSTEM" "✨ Development servers are running!" "Cyan"
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Log "BACKEND" "http://localhost:8000 (API)" "Blue"
    Write-Log "BACKEND" "http://localhost:8000/docs (API Docs)" "Blue"
    Write-Log "FRONTEND" "http://localhost:5173 (UI)" "Green"
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Log "SYSTEM" "Press Ctrl+C to stop all servers" "Yellow"
    Write-Host ""

    # Monitor jobs
    while ($true) {
        $BackendState = $BackendJob.State
        $FrontendState = $FrontendJob.State

        if ($BackendState -eq "Failed" -or $FrontendState -eq "Failed") {
            Write-Log "ERROR" "One or more servers failed" "Red"
            $Script:ExitCode = 1
            Cleanup
        }

        if ($BackendState -eq "Completed" -or $FrontendState -eq "Completed") {
            Write-Log "SYSTEM" "One or more servers stopped" "Yellow"
            $Script:ExitCode = 1
            Cleanup
        }

        Start-Sleep -Seconds 1
    }

} catch {
    Write-Log "ERROR" "Failed to start servers: $_" "Red"
    $Script:ExitCode = 1
    Cleanup
}

