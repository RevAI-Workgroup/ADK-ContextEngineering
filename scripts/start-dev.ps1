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
    
    # Kill any remaining Python (uvicorn) processes on port 8000
    Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | 
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    
    # Kill any Node (vite) processes on port 5173
    Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue | 
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    
    Write-Log "SYSTEM" "All servers stopped" "Yellow"
    exit $Script:ExitCode
}

# Set up cleanup on exit
Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action { Cleanup }

# Print header
Write-Host ""
Write-Host "╔═══════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   ADK Context Engineering - Dev Server    ║" -ForegroundColor Cyan
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

function Test-BackendHealth {
    param(
        [int]$MaxAttempts = 30,
        [int]$IntervalSeconds = 1
    )
    
    $attempts = 0
    while ($attempts -lt $MaxAttempts) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 1 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Write-Log "BACKEND" "Health check passed - backend is ready!" "Green"
                return $true
            }
        } catch {
            # Backend not ready yet, continue polling
        }
        
        $attempts++
        if ($attempts -lt $MaxAttempts) {
            Start-Sleep -Seconds $IntervalSeconds
        }
    }
    
    Write-Log "BACKEND" "Health check failed - backend did not become ready in time" "Yellow"
    return $false
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

    # Wait for backend to be ready via health check
    Write-Log "BACKEND" "Waiting for backend to be ready..." "Cyan"
    Start-Sleep -Seconds 2  # Give backend a moment to start
    $backendReady = Test-BackendHealth
    
    if (-not $backendReady) {
        Write-Log "BACKEND" "Proceeding with frontend startup despite health check timeout" "Yellow"
    }

    # Start frontend only after backend is ready
    Write-Log "SYSTEM" "Backend is ready, starting frontend..." "Cyan"
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

