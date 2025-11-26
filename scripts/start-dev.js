#!/usr/bin/env node

/**
 * Platform-agnostic development server startup script
 * Starts both backend (FastAPI) and frontend (Vite) concurrently
 * Handles graceful shutdown on Ctrl+C
 */

const { spawn } = require('child_process');
const http = require('http');
const path = require('path');
const os = require('os');

const rootDir = path.join(__dirname, '..');
const isWindows = os.platform() === 'win32';

// Store child processes for cleanup
const processes = [];

// Color codes for terminal output
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  blue: '\x1b[34m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  red: '\x1b[31m',
  cyan: '\x1b[36m'
};

function log(prefix, message, color = colors.reset) {
  console.log(`${color}${colors.bright}[${prefix}]${colors.reset} ${message}`);
}

/**
 * Check if backend is ready by polling the /health endpoint
 * @param {number} maxAttempts - Maximum number of attempts
 * @param {number} intervalMs - Interval between attempts in milliseconds
 * @returns {Promise<boolean>} - True if backend is ready
 */
function checkBackendHealth(maxAttempts = 30, intervalMs = 1000) {
  return new Promise((resolve) => {
    let attempts = 0;
    let resolved = false;
    let pendingTimeouts = [];
    let currentRequest = null;
    
    const cleanup = () => {
      // Clear all pending timeouts
      pendingTimeouts.forEach(timeout => clearTimeout(timeout));
      pendingTimeouts = [];
      
      // Abort current request if it exists
      if (currentRequest) {
        currentRequest.destroy();
        currentRequest = null;
      }
    };
    
    const checkHealth = () => {
      // Stop if already resolved
      if (resolved) {
        return;
      }
      
      attempts++;
      
      const req = http.get('http://localhost:8000/health', (res) => {
        // Stop if already resolved
        if (resolved) {
          req.destroy();
          return;
        }
        
        if (res.statusCode === 200) {
          resolved = true;
          log('BACKEND', 'Health check passed - backend is ready!', colors.green);
          cleanup();
          resolve(true);
        } else {
          if (attempts < maxAttempts) {
            const timeout = setTimeout(checkHealth, intervalMs);
            pendingTimeouts.push(timeout);
          } else {
            resolved = true;
            log('BACKEND', 'Health check failed - backend did not become ready in time', colors.yellow);
            cleanup();
            resolve(false);
          }
        }
      });
      
      currentRequest = req;
      
      req.on('error', () => {
        // Stop if already resolved
        if (resolved) {
          return;
        }
        
        if (attempts < maxAttempts) {
          // Backend not ready yet, try again
          const timeout = setTimeout(checkHealth, intervalMs);
          pendingTimeouts.push(timeout);
        } else {
          resolved = true;
          log('BACKEND', 'Health check failed - backend did not become ready in time', colors.yellow);
          cleanup();
          resolve(false);
        }
      });
      
      req.setTimeout(500, () => {
        req.destroy();
        currentRequest = null;
        
        // Stop if already resolved
        if (resolved) {
          return;
        }
        
        if (attempts < maxAttempts) {
          const timeout = setTimeout(checkHealth, intervalMs);
          pendingTimeouts.push(timeout);
        } else {
          resolved = true;
          log('BACKEND', 'Health check failed - backend did not become ready in time', colors.yellow);
          cleanup();
          resolve(false);
        }
      });
    };
    
    // Start checking after a short delay to give backend time to start
    const initialTimeout = setTimeout(checkHealth, 2000);
    pendingTimeouts.push(initialTimeout);
  });
}

function startBackend() {
  return new Promise((resolve, reject) => {
    log('BACKEND', 'Starting FastAPI server...', colors.blue);

    let backendProcess;
    let settled = false;
    
    if (isWindows) {
      // Windows: Use cmd to run activation and uvicorn
      backendProcess = spawn('cmd', ['/c', `venv\\Scripts\\activate && set PYTHONPATH=${rootDir} && uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000`], {
        cwd: rootDir,
        shell: true,
        stdio: 'pipe'
      });
    } else {
      // Unix (macOS/Linux): Use bash to source activation and run uvicorn
      // Match start-dev.sh: export PYTHONPATH="${PYTHONPATH}:$(pwd)"
      backendProcess = spawn('bash', ['-c', `source venv/bin/activate && export PYTHONPATH="$PYTHONPATH:${rootDir}" && uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000`], {
        cwd: rootDir,
        stdio: 'pipe'
      });
    }

    processes.push(backendProcess);

    backendProcess.stdout.on('data', (data) => {
      const output = data.toString().trim();
      if (output) {
        output.split('\n').forEach(line => {
          log('BACKEND', line, colors.blue);
        });
      }
    });

    backendProcess.stderr.on('data', (data) => {
      const output = data.toString().trim();
      if (output) {
        output.split('\n').forEach(line => {
          log('BACKEND', line, colors.blue);
        });
      }
    });

    backendProcess.on('error', (error) => {
      if (!settled) {
        settled = true;
        log('BACKEND', `Error: ${error.message}`, colors.red);
        reject(error);
      }
    });

    backendProcess.on('exit', (code) => {
      if (code !== 0 && code !== null) {
        log('BACKEND', `Exited with code ${code}`, colors.red);
        if (!settled) {
          settled = true;
          reject(new Error(`Backend process exited with code ${code}`));
        }
      }
    });

    // Wait for backend to be ready via health check
    log('BACKEND', 'Waiting for backend to be ready...', colors.cyan);
    checkBackendHealth().then((isReady) => {
      if (!settled) {
        settled = true;
        if (isReady) {
          resolve(backendProcess);
        } else {
          // Backend started but health check failed - still resolve to allow frontend to start
          // The user can manually reload if needed
          log('BACKEND', 'Proceeding with frontend startup despite health check timeout', colors.yellow);
          resolve(backendProcess);
        }
      }
    });
  });
}

function startFrontend() {
  return new Promise((resolve, reject) => {
    log('FRONTEND', 'Starting Vite dev server...', colors.green);

    const frontendDir = path.join(rootDir, 'frontend');
    let settled = false;
    let startupTimer;
    
    // Use pnpm to start the frontend
    const frontendProcess = spawn(isWindows ? 'pnpm.cmd' : 'pnpm', ['dev'], {
      cwd: frontendDir,
      stdio: 'pipe',
      shell: isWindows
    });

    processes.push(frontendProcess);

    frontendProcess.stdout.on('data', (data) => {
      const output = data.toString().trim();
      if (output) {
        output.split('\n').forEach(line => {
          log('FRONTEND', line, colors.green);
        });
      }
    });

    frontendProcess.stderr.on('data', (data) => {
      const output = data.toString().trim();
      if (output) {
        output.split('\n').forEach(line => {
          log('FRONTEND', line, colors.green);
        });
      }
    });

    frontendProcess.on('error', (error) => {
      if (!settled) {
        settled = true;
        clearTimeout(startupTimer);
        log('FRONTEND', `Error: ${error.message}`, colors.red);
        reject(error);
      }
    });

    frontendProcess.on('exit', (code) => {
      if (code !== 0 && code !== null) {
        log('FRONTEND', `Exited with code ${code}`, colors.red);
        if (!settled) {
          settled = true;
          clearTimeout(startupTimer);
          reject(new Error(`Frontend process exited with code ${code}`));
        }
      }
    });

    // Give frontend a moment to start
    startupTimer = setTimeout(() => {
      if (!settled) {
        settled = true;
        resolve(frontendProcess);
      }
    }, 1000);
  });
}

function cleanup() {
  log('SYSTEM', 'Shutting down servers...', colors.yellow);
  
  processes.forEach((proc) => {
    if (proc && !proc.killed) {
      // On Windows, use taskkill to ensure child processes are also killed
      if (isWindows) {
        spawn('taskkill', ['/pid', proc.pid, '/f', '/t']);
      } else {
        // On Unix, kill the process group
        try {
          process.kill(-proc.pid);
        } catch (e) {
          proc.kill('SIGTERM');
        }
      }
    }
  });

  setTimeout(() => {
    log('SYSTEM', 'All servers stopped', colors.yellow);
    process.exit(0);
  }, 1000);
}

// Handle termination signals
process.on('SIGINT', cleanup);
process.on('SIGTERM', cleanup);
process.on('exit', cleanup);

// Main execution
async function main() {
  console.log(`\n${colors.cyan}${colors.bright}╔══════════════════════════════════════════╗${colors.reset}`);
  console.log(`${colors.cyan}${colors.bright}║   ADK Context Engineering - Dev Server   ║${colors.reset}`);
  console.log(`${colors.cyan}${colors.bright}╚══════════════════════════════════════════╝${colors.reset}\n`);
  
  log('SYSTEM', `Platform: ${os.platform()} (${os.arch()})`, colors.cyan);
  log('SYSTEM', `Node.js: ${process.version}`, colors.cyan);
  log('SYSTEM', 'Starting development servers...\n', colors.cyan);

  try {
    const fs = require('fs');

    // Check if venv exists
    const venvPath = isWindows
      ? path.join(rootDir, 'venv', 'Scripts', 'activate.bat')
      : path.join(rootDir, 'venv', 'bin', 'activate');

    if (!fs.existsSync(venvPath)) {
      log('ERROR', 'Virtual environment not found!', colors.red);
      log('ERROR', 'Please run: python -m venv venv', colors.red);
      log('ERROR', `Then: ${isWindows ? 'venv\\Scripts\\activate && pip install -r requirements.txt' : 'source venv/bin/activate && pip install -r requirements.txt'}`, colors.red);
      process.exit(1);
    }

    // Check if workspace dependencies are installed
    const nodeModulesPath = path.join(rootDir, 'node_modules');
    const frontendNodeModulesPath = path.join(rootDir, 'frontend', 'node_modules');

    if (!fs.existsSync(nodeModulesPath)) {
      log('ERROR', 'Workspace dependencies not found!', colors.red);
      log('ERROR', 'Please run: pnpm install', colors.red);
      log('ERROR', '(Run from project root, not from frontend directory)', colors.red);
      process.exit(1);
    }

    // Warn if frontend has its own node_modules (incorrect workspace setup)
    if (fs.existsSync(frontendNodeModulesPath)) {
      log('WARNING', 'Frontend has its own node_modules directory!', colors.yellow);
      log('WARNING', 'This may indicate incorrect workspace setup.', colors.yellow);
      const cleanupCmd = isWindows
        ? 'rmdir /s /q frontend\\node_modules && pnpm install'
        : 'rm -rf frontend/node_modules && pnpm install';
      log('WARNING', `Consider running: ${cleanupCmd}`, colors.yellow);
    }

    // Initialize Vector Store (if not already initialized)
    log('VECTOR STORE', 'Checking ChromaDB initialization...', colors.cyan);
    try {
      const initCmd = isWindows
        ? `venv\\Scripts\\activate && python scripts\\init_vector_store.py`
        : `source venv/bin/activate && python3 scripts/init_vector_store.py`;
      
      const shell = isWindows ? 'cmd' : 'bash';
      const shellArgs = isWindows ? ['/c', initCmd] : ['-c', initCmd];
      
      const initProcess = spawn(shell, shellArgs, {
        cwd: rootDir,
        stdio: 'pipe',
        shell: true
      });

      await new Promise((resolve) => {
        initProcess.on('close', (code) => {
          if (code === 0) {
            log('VECTOR STORE', 'Vector store initialized successfully', colors.cyan);
          } else {
            log('WARNING', 'Vector store initialization failed (non-critical)', colors.yellow);
            const activateCmd = isWindows 
              ? 'venv\\Scripts\\activate && python scripts\\init_vector_store.py'
              : 'source venv/bin/activate && python3 scripts/init_vector_store.py';
            log('WARNING', `You can manually initialize later with: ${activateCmd}`, colors.yellow);
          }
          resolve();
        });
      });
    } catch (error) {
      log('WARNING', 'Vector store initialization failed (non-critical)', colors.yellow);
      log('WARNING', `Error: ${error.message}`, colors.yellow);
    }

    // Start backend first and wait for it to be ready
    log('SYSTEM', 'Starting backend server...', colors.cyan);
    await startBackend();
    
    // Only start frontend after backend is ready
    log('SYSTEM', 'Backend is ready, starting frontend...', colors.cyan);
    await startFrontend();

    console.log(`\n${colors.cyan}${colors.bright}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${colors.reset}`);
    log('SYSTEM', '✨ Development servers are running!', colors.cyan);
    console.log(`${colors.cyan}${colors.bright}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${colors.reset}`);
    log('BACKEND', 'http://localhost:8000 (API)', colors.blue);
    log('BACKEND', 'http://localhost:8000/docs (API Docs)', colors.blue);
    log('FRONTEND', 'http://localhost:5173 (UI)', colors.green);
    console.log(`${colors.cyan}${colors.bright}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${colors.reset}`);
    log('SYSTEM', 'Press Ctrl+C to stop all servers\n', colors.yellow);

  } catch (error) {
    log('ERROR', `Failed to start servers: ${error.message}`, colors.red);
    cleanup();
    process.exit(1);
  }
}

main();

