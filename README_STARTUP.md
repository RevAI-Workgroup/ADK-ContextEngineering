# Development Server Startup Scripts

This project includes multiple platform-specific startup scripts to launch both the backend (FastAPI) and frontend (Vite) servers simultaneously.

## Prerequisites

Before running any startup script, ensure you have:

1. **Python virtual environment** set up:
   ```bash
   python -m venv venv
   ```

2. **Python dependencies** installed:
   - **macOS/Linux**:
     ```bash
     source venv/bin/activate
     pip install -r requirements.txt
     ```
   - **Windows (cmd)**:
     ```cmd
     venv\Scripts\activate
     pip install -r requirements.txt
     ```
   - **Windows (PowerShell)**:
     ```powershell
     .\venv\Scripts\Activate.ps1
     pip install -r requirements.txt
     ```

3. **Frontend dependencies** installed:
   ```bash
   cd frontend
   pnpm install
   cd ..
   ```

## Usage

### Option 1: Node.js Script (Cross-Platform - Recommended)

This is the **recommended** method as it works identically on all platforms.

```bash
# Install dependencies first (one-time setup)
pnpm install

# Start development servers
pnpm dev
# or
pnpm start
```

**Advantages:**
- ✅ Truly platform-agnostic
- ✅ Colored output for both servers
- ✅ Proper cleanup on Ctrl+C
- ✅ Unified experience across all platforms

### Option 2: Unix Shell Script (macOS/Linux)

```bash
# Make executable (first time only)
chmod +x start-dev.sh

# Run the script
./start-dev.sh
```

### Option 3: Windows Batch Script

```cmd
start-dev.bat
```

**Note:** This opens separate console windows for backend and frontend. Close the main window to stop all servers.

### Option 4: Windows PowerShell Script

```powershell
# Enable script execution (first time only, run as Administrator)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Run the script
.\start-dev.ps1
```

## What Happens When Scripts Run

All scripts perform the following:

1. **Check Prerequisites**: Verify that the Python virtual environment exists
2. **Start Backend**: Launch FastAPI server at `http://localhost:8000`
3. **Start Frontend**: Launch Vite dev server at `http://localhost:5173`
4. **Monitor Processes**: Keep both servers running
5. **Cleanup on Exit**: Properly terminate both servers when you press Ctrl+C

## Accessing the Application

Once the servers are running:

- **Frontend UI**: [http://localhost:5173](http://localhost:5173)
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)

## Stopping the Servers

### Node.js / Shell / PowerShell Scripts
Press **Ctrl+C** in the terminal where the script is running. The scripts will:
- Catch the interrupt signal
- Gracefully shut down both backend and frontend
- Clean up all processes

### Batch Script (Windows)
Press any key in the command window, or simply close the window. This will:
- Terminate all related processes
- Close both backend and frontend windows

## Troubleshooting

### Virtual Environment Not Found

**Error**: `Virtual environment not found`

**Solution**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Port Already in Use

**Error**: `Address already in use` or similar

**Solution**: Kill existing processes on ports 8000 or 5173

- **macOS/Linux**:
  ```bash
  lsof -ti:8000 | xargs kill -9
  lsof -ti:5173 | xargs kill -9
  ```

- **Windows (PowerShell)**:
  ```powershell
  Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process -Force
  Get-Process -Id (Get-NetTCPConnection -LocalPort 5173).OwningProcess | Stop-Process -Force
  ```

### pnpm Not Found

**Error**: `pnpm: command not found`

**Solution**: Install pnpm globally
```bash
npm install -g pnpm
```

### Permission Denied (Unix/macOS)

**Error**: `Permission denied` when running `./start-dev.sh`

**Solution**: Make the script executable
```bash
chmod +x start-dev.sh
```

### PowerShell Script Execution Policy Error

**Error**: `cannot be loaded because running scripts is disabled`

**Solution**: Enable script execution
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Script Details

### Node.js Script (`scripts/start-dev.js`)
- Uses child processes to spawn backend and frontend
- Platform detection for Windows vs Unix
- Colored console output with prefixes
- Graceful shutdown handling
- Automatic process cleanup

### Shell Script (`start-dev.sh`)
- Uses bash for maximum compatibility
- Background processes with PID tracking
- Signal handlers for cleanup
- Colored output using ANSI codes

### Batch Script (`start-dev.bat`)
- Opens separate console windows
- Uses `start` command with window titles
- Window-based process management
- Closes all windows on exit

### PowerShell Script (`start-dev.ps1`)
- Uses PowerShell jobs for process management
- Built-in cleanup handlers
- Modern PowerShell 7+ compatible
- Colored output using Write-Host

## Recommended Workflow

For the best development experience:

1. **Use the Node.js script** (`pnpm dev`) as it provides:
   - Consistent behavior across all platforms
   - Better process management
   - Colored, prefixed output for easy debugging
   - Proper cleanup on exit

2. **Use platform-specific scripts** if you prefer native shell integration or need to customize behavior

3. **Add to your shell aliases** for convenience:
   ```bash
   # Add to ~/.bashrc or ~/.zshrc
   alias adk-dev="cd /path/to/ADK-ContextEngineering && pnpm dev"
   ```

## Development Tips

- **Hot Reload**: Both backend (`--reload`) and frontend (Vite) support hot reloading
- **Logs**: All output is prefixed with `[BACKEND]` or `[FRONTEND]` for easy identification
- **Debug Mode**: Check individual logs if needed:
  - Backend: `tail -f backend.log`
  - Frontend: `tail -f frontend/frontend.log`

## Contributing

When adding new startup features:
1. Update all platform-specific scripts
2. Test on Windows, macOS, and Linux
3. Update this README with any new requirements or behaviors

