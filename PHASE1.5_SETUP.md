# Phase 1.5 Setup Instructions

This document provides step-by-step instructions for setting up and running the Context Engineering Sandbox with the new Phase 1.5 Web UI.

---

## Prerequisites

### Required
1. **Python 3.11+** - Backend runtime
2. **Node.js 18+** and **npm** - Frontend runtime
3. **Ollama** - Local LLM runtime ([install from ollama.com](https://ollama.com))

### Optional
- **Docker** and **Docker Compose** - For containerized deployment

---

## Quick Start (Recommended)

### Option 1: Docker Compose (Easiest)

```bash
# 1. Ensure Ollama is running
ollama serve

# 2. Pull the Qwen3 model
ollama pull qwen3:4b

# 3. Build and run all services
docker-compose -f docker/docker-compose.yml up --build

# 4. Access the web UI
# Frontend: http://localhost
# Backend API: http://localhost:8000
```

### Option 2: Development Mode (For Development)

**Terminal 1 - Backend:**
```bash
# 1. Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\Activate.ps1  # Windows

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Start FastAPI backend
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Backend will be available at http://localhost:8000
```

**Terminal 2 - Frontend:**
```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Start development server
npm run dev

# Frontend will be available at http://localhost:5173
```

**Terminal 3 - Ollama:**
```bash
# Make sure Ollama is running
ollama serve

# Verify qwen3:4b model is downloaded
ollama list
```

---

## Detailed Setup

### 1. Backend Setup

**IMPORTANT:** The project requires Python 3.11+ and uses a virtual environment.

```bash
# Verify Python 3.11 is installed
python3.11 --version  # Should show 3.11.x

# Create virtual environment (if not already done)
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# OR on Windows:
# .\venv\Scripts\Activate.ps1

# Install all dependencies
pip install -r requirements.txt

# Create .env file (optional - defaults work fine)
cp .env.example .env
```

**Backend Environment Variables (Optional):**
```env
# Ollama Configuration
OLLAMA_HOST=http://localhost:11434

# FastAPI Configuration
API_HOST=0.0.0.0
API_PORT=8000
```

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Create environment file
cp .env.example .env
```

**Frontend Environment Variables:**
```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_ENV=development
```

### 3. Ollama Setup

```bash
# Install Ollama from https://ollama.com

# Start Ollama service
ollama serve

# Download Qwen3 4B model (2.5 GB)
ollama pull qwen3:4b

# Verify it's working
ollama list
```

---

## Running the Application

### Development Mode

**Start Backend:**
```bash
# Option A: Use helper script (easiest)
./start_backend.sh

# Option B: Manual activation
source venv/bin/activate
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

**Start Frontend:**
```bash
# From frontend directory
cd frontend
npm run dev
```

### Production Mode (Docker)

```bash
# Build and start all services
docker-compose -f docker/docker-compose.yml up --build -d

# View logs
docker-compose -f docker/docker-compose.yml logs -f

# Stop services
docker-compose -f docker/docker-compose.yml down
```

---

## Verification

### Backend API

```bash
# Health check
curl http://localhost:8000/health

# Get available tools
curl http://localhost:8000/api/tools

# Get metrics
curl http://localhost:8000/api/metrics
```

### Frontend

1. Open browser to http://localhost:5173 (dev) or http://localhost (docker)
2. Navigate to Chat page
3. Send a test message: "What is 5 + 3?"
4. Verify agent responds using the calculate tool

### WebSocket

The WebSocket endpoint is at: `ws://localhost:8000/api/chat/ws`

Test with a WebSocket client or use the frontend chat interface.

---

## Features

### Pages

1. **Home** (`/`)
   - Project overview
   - Phase status
   - Quick navigation

2. **Chat** (`/chat`)
   - Interactive agent chat
   - Real-time streaming
   - Thinking process visualization
   - Tool call display

3. **Metrics** (`/metrics`)
   - Performance dashboard
   - Phase comparisons
   - Trend charts
   - Improvement tracking

### Backend API Endpoints

- `POST /api/chat` - Synchronous chat
- `WS /api/chat/ws` - WebSocket streaming
- `GET /api/metrics` - All metrics
- `GET /api/metrics/phase/{phase_id}` - Phase-specific metrics
- `GET /api/metrics/comparison` - Phase comparison
- `GET /api/tools` - Available tools
- `GET /api/tools/{tool_name}` - Tool details

---

## Troubleshooting

### Frontend won't start

**Problem**: `npm run dev` fails
**Solution**:
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Backend API errors

**Problem**: Backend returns 500 errors
**Solution**:
1. Check if Ollama is running: `ollama list`
2. Verify qwen3:4b model: `ollama pull qwen3:4b`
3. Check backend logs for errors

### WebSocket connection fails

**Problem**: "WebSocket connection error"
**Solution**:
1. Verify backend is running on port 8000
2. Check CORS configuration in `src/api/main.py`
3. Ensure frontend `VITE_WS_URL` is set correctly

### Docker build fails

**Problem**: Docker compose fails to build
**Solution**:
```bash
# Clean up Docker
docker-compose -f docker/docker-compose.yml down -v
docker system prune -f

# Rebuild
docker-compose -f docker/docker-compose.yml up --build
```

### Agent responds slowly

**Expected**: First response takes 30-45 seconds
**Reason**: Qwen3 4B model reasoning + tool execution
**Solution**: This is normal behavior for local LLMs

---

## Development

### Frontend Development

```bash
cd frontend

# Run linter
npm run lint

# Build for production
npm run build

# Preview production build
npm run preview
```

### Backend Development

```bash
# Run with auto-reload
uvicorn src.api.main:app --reload

# Run tests
pytest tests/

# Check code style
black src/ --check
flake8 src/
```

---

## Next Steps

With Phase 1.5 complete, you can now:

1. ✅ Chat with the agent via beautiful web UI
2. ✅ View real-time metrics and comparisons
3. ✅ See agent thinking and tool calls visualized
4. 🚀 Ready for **Phase 2**: RAG Implementation with document upload

---

## Additional Resources

- **Backend API Docs**: http://localhost:8000/docs (when running)
- **Frontend README**: `frontend/README.md`
- **Phase 1.5 Summary**: `docs/phase_summaries/phase1_5_summary.md`
- **Main README**: `README.md`
- **AG-UI Protocol**: https://github.com/ag-ui-protocol/ag-ui

---

## Support

If you encounter issues:

1. Check this troubleshooting guide
2. Review the error logs
3. Verify all prerequisites are installed
4. Check that Ollama is running with qwen3:4b

---

*Last Updated: 2025-10-31*
*Phase 1.5 Complete ✅*

