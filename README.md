# 🎯 Context Engineering Sandbox

> A demonstration project showcasing the progressive gains of context engineering techniques in LLM applications using Google ADK with local Ollama models.

## 📋 Project Overview

This project is a **modular experimentation platform** for context engineering techniques. Instead of linear phase progression, it enables dynamic comparison of different configurations through a toggleable architecture, measuring the impact of each technique on:
- **Effectiveness**: Answer accuracy, relevance, hallucination rate
- **Efficiency**: Latency, token usage, cost
- **Scalability**: Throughput, memory usage

**Key Innovation**: Run the same query with different context engineering techniques enabled/disabled, then compare results side-by-side to measure real impact.

## 🚀 Technology Stack

### Backend
- **LLM Framework**: Google ADK v1.17.0 (Agentic Development Kit)
- **Local LLM**: Ollama with Qwen3 4B (2.5 GB)
- **Model Integration**: LiteLLM v1.72.6
- **API Framework**: FastAPI + Uvicorn with WebSocket support
- **Vector Database**: ChromaDB (local, persistent) - Phase 2+
- **Embeddings**: sentence-transformers (local) - Phase 2+
- **Language**: Python 3.11+

### Frontend (Phase 1.5+)
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **UI Library**: Shadcn/UI (built on Tailwind CSS)
- **Agent Protocol**: AG-UI (CopilotKit)
- **Charts**: Recharts
- **HTTP Client**: Axios
- **Routing**: React Router

## 📊 Project Status

**Current Phase**: Phase 2 - Modular Platform Infrastructure ✅ **COMPLETE**

### Phase 0 Baseline Metrics

| Metric | Value |
|--------|-------|
| ROUGE-1 F1 (mean) | 0.3149 |
| ROUGE-2 F1 (mean) | 0.1598 |
| ROUGE-L F1 (mean) | 0.2509 |
| Relevance Score (mean) | 0.5698 |
| Hallucination Rate (mean) | 0.0422 |
| Latency (ms) | ~0 |
| Tokens/Query | 29.27 |

## 🗺️ Implementation Phases

- ✅ **Phase 0**: Foundation & Benchmarking (Complete)
- ✅ **Phase 1**: MVP Agent with Google ADK (Complete)
- ✅ **Phase 1.5**: Web UI Development (Complete)
- ✅ **Phase 2**: Modular Platform Infrastructure (Complete - Toggleable architecture built!)
- ⏳ **Phase 3**: RAG Module (Next - First technique: vector retrieval)
- ⏳ **Phase 4**: Compression, Caching & Memory Modules (Efficiency techniques)
- ⏳ **Phase 5**: Reranking & Hybrid Search Modules (Quality techniques)
- ⏳ **Phase 6**: Advanced Technique Modules (Graph RAG, adaptive chunking)
- ⏳ **Phase 7**: System Integration & Optimization

**Architecture Shift**: Each phase after Phase 2 implements ONE technique as a pluggable module that can be toggled and configured independently.

## 🏗️ Project Structure

```
context-engineering-sandbox/
├── frontend/              # Phase 1.5: React Web UI
│   ├── src/
│   │   ├── components/   # React components (UI, chat, metrics)
│   │   ├── pages/        # Route pages
│   │   ├── hooks/        # Custom React hooks
│   │   ├── services/     # API services
│   │   └── types/        # TypeScript types
│   └── public/           # Static assets
├── src/                   # Backend Python source
│   ├── core/             # Core configuration and utilities
│   ├── evaluation/       # Metrics and benchmarking framework
│   ├── retrieval/        # Vector search and RAG (Phase 2+)
│   ├── memory/           # Conversation memory (Phase 4+)
│   ├── compression/      # Context compression (Phase 5+)
│   ├── advanced/         # Graph RAG, routing (Phase 6+)
│   └── api/              # FastAPI endpoints (Phase 1.5+)
├── context_engineering_agent/  # ADK agent directory
├── configs/              # YAML configuration files
├── data/
│   ├── test_sets/        # Benchmark datasets
│   └── knowledge_base/   # Documents for RAG
├── docker/               # Docker configuration
├── scripts/              # Utility scripts
├── docs/                 # Documentation
└── tests/                # Test suites
```

## 🚀 Quick Start

### 1. Prerequisites

**Required:**
- Python 3.11+
- [Ollama](https://ollama.com) installed and running

**Install Ollama:**
```bash
# Download from https://ollama.com
# Or on macOS:
brew install ollama

# Start Ollama service (if not auto-started)
ollama serve
```

### 2. Setup Environment

```bash
# Clone the repository
git clone https://github.com/RevAI-Workgroup/ADK-ContextEngineering.git
cd ADK-ContextEngineering

# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\Activate.ps1

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Download the LLM Model

```bash
# Download Qwen3 4B model (2.5 GB) - takes 1-2 minutes
ollama pull qwen3:4b

# Verify model is available
ollama list
```

### 4. Run the Application

**Option A: Docker (Recommended - Full Stack):**
```bash
# Build and run both frontend and backend
docker-compose -f docker/docker-compose.yml up --build

# Access the web UI at http://localhost
```

**Option B: Development Mode (Backend + Frontend):**

Terminal 1 - Backend:
```bash
# Start FastAPI backend
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

Terminal 2 - Frontend:
```bash
# Install frontend dependencies (first time only)
cd frontend
npm install

# Start frontend dev server
npm run dev

# Access the web UI at http://localhost:5173
```

**Option C: CLI Only (No Web UI):**
```bash
# Interactive mode
adk run context_engineering_agent

# Single query
echo "What is 5 plus 3?" | adk run context_engineering_agent

# ADK's built-in web interface
adk web
```

### 5. Using Phase 2 Features (Configuration & Run Comparison)

**Access the Web UI:**
```bash
# After starting the application (Option A, B, or C above)
# Navigate to http://localhost:5173 (dev mode) or http://localhost (Docker)
```

**Configuration Panel:**
1. Open the Chat page
2. Click the "⚙️ Configuration" button to expand the panel
3. **Simple Tab:**
   - Toggle techniques on/off (RAG, Compression, Reranking, Caching, Hybrid Search, Memory)
   - Select a preset: Baseline, Basic RAG, Advanced RAG, or Full Stack
4. **Advanced Tab:**
   - Fine-tune parameters for each enabled technique
   - Adjust chunk sizes, top-k values, thresholds, etc.

**Run History & Comparison:**
1. Execute queries with different configurations
2. View last 8 runs in the Run History sidebar (on Chat page)
3. Select multiple runs (checkboxes) to compare
4. Click "Compare Selected" to see side-by-side analysis
5. Export comparison results to JSON

**Metrics Dashboard:**
1. Navigate to the Metrics page
2. Select runs to compare using the multi-select checkboxes
3. Filter by date range, query text, or enabled techniques
4. View charts: Latency, Token Usage, Relevance, Accuracy, Technique Impact
5. Analyze metrics summary table with best/worst highlighting

### 6. Run Tests (Optional)

**Phase 2 Backend Tests:**
```bash
# Run all Phase 2 unit tests (114 tests)
pytest tests/unit/test_context_config.py -v
pytest tests/unit/test_run_history.py -v
pytest tests/unit/test_modular_pipeline.py -v

# Run all tests
pytest tests/ -v

# Test Phase 2 API endpoints
python scripts/test_phase2_api.py
```

**Manual Test Script (Phase 1 Tools):**
```bash
./scripts/test_adk_agent.sh
# Tests all 4 tools with example queries
```

**Phase 0 Baseline (For Comparison):**
```bash
# Generate benchmark datasets (if not already done)
python scripts/create_benchmarks.py

# Run Phase 0 baseline evaluation
python scripts/run_evaluation.py
```

## 📈 Evaluation Framework

The project includes a comprehensive evaluation framework:

- **Metrics Collection**: Automated tracking of accuracy, efficiency, and quality metrics
- **Benchmark Datasets**: 15 diverse test cases across technical, general, reasoning, and factual categories
- **Paired Comparison Testing**: Framework for comparing techniques on identical test cases to measure relative gains
- **Results Storage**: Detailed JSON reports with aggregate statistics

## 🔧 Configuration

All configuration is managed through YAML files in the `configs/` directory:

- `models.yaml` - LLM and embedding model configuration
- `retrieval.yaml` - Vector search and chunking strategies
- `evaluation.yaml` - Metrics and benchmarking settings

**Environment Variable Override**: Any config value can be overridden via environment variables with automatic type conversion:
```bash
# YAML: models.ollama.timeout: 120 (int)
export MODELS_OLLAMA_TIMEOUT=240  # Automatically converted to int 240

# YAML: models.ollama.enabled: true (bool)
export MODELS_OLLAMA_ENABLED=yes  # Automatically converted to bool True
```

## 📚 Documentation

- **[BACKLOG.md](BACKLOG.md)** - Detailed implementation plan with modular architecture
- **[.context/](.context/)** - AI assistant context files
- **[docs/phase_summaries/](docs/phase_summaries/)** - Phase completion reports

### Experimentation Workflow

The platform enables systematic comparison of context engineering techniques:

1. **Configure**: Toggle techniques on/off, adjust parameters, select presets
2. **Run**: Execute query with current configuration (automatically saved to history)
3. **Store**: Last 8 runs kept in history with full context
4. **Compare**: Select multiple runs to see side-by-side differences
5. **Analyze**: View metric deltas in Metrics dashboard
6. **Iterate**: Refine configuration based on insights

**Example**: Run "What is RAG?" three times:
- Run 1: Baseline (no techniques) → Accuracy: 0.85
- Run 2: +RAG enabled → Accuracy: 0.95 (+10%)
- Run 3: +RAG +Compression → Accuracy: 0.93, Tokens: -22%

Compare all three to see which configuration offers the best tradeoff.

## 🔬 Current Phase: Phase 1 ✅ COMPLETE

Phase 1 integrates Google ADK with Ollama backend:

### ✅ Completed
- Google ADK v1.17.0 + LiteLLM v1.72.6 integration
- Ollama backend configured with Qwen3 4B model (2.5 GB)
- ADK agent directory structure: `context_engineering_agent/`
- 4 working tools implemented and tested:
  - `calculate` - Safe arithmetic (AST-based)
  - `count_words` - Word counting
  - `get_current_time` - Timezone-aware queries
  - `analyze_text` - Comprehensive text analysis
- Agent successfully runs via `adk run context_engineering_agent`
- Tool calling verified: Agent correctly selects and executes tools
- Comprehensive documentation: [Phase 1 Summary](docs/phase_summaries/phase1_summary.md)

### 🧪 Test Results
- ✅ Calculator: `5 + 3 = 8`, `123 / 4 = 30.75`
- ✅ Word counter: Correctly counted 6 words
- ✅ Time tool: Retrieved America/New_York time
- ✅ Agent reasoning: Shows clear decision-making process

### 🎯 Key Decisions
- **Skipped**: File system & code execution tools (not needed for context engineering)
- **Skipped**: Custom FastAPI (use ADK's built-in `adk web` and `adk run`)
- **Deferred**: Web search to Phase 3 (external context retrieval)

## 🎨 Phase 1.5: Web UI Development ✅ COMPLETE

Phase 1.5 delivers a modern React frontend with AG-UI integration:

### ✅ Completed
- **Frontend**: React 18 + TypeScript with Vite
- **UI Framework**: Shadcn/UI components on Tailwind CSS
- **AG-UI Protocol**: CopilotKit integration for agent-user interaction
- **Real-time Communication**: WebSocket support for streaming responses
- **Pages**: Home, Chat, Metrics dashboard with charts
- **Backend API**: FastAPI with WebSocket endpoints
- **Docker**: Multi-container setup with Nginx reverse proxy
- **Documentation**: Comprehensive [Phase 1.5 Summary](docs/phase_summaries/phase1_5_summary.md)

### 🎯 Key Features
- Interactive chat interface with thinking visualization
- Real-time metrics dashboard with phase comparisons
- Tool call display and agent reasoning transparency
- Responsive design with dark mode support
- WebSocket streaming for live agent updates

## 🏗️ Phase 2: Modular Platform Infrastructure ✅ COMPLETE

**Completion Date:** November 5, 2025

Phase 2 successfully transformed the project into a modular experimentation platform with toggleable context engineering techniques.

### ✅ Backend Implementation

**Configuration System** (`src/core/context_config.py`)
- 6 technique modules with full configuration: RAG, Compression, Reranking, Caching, Hybrid Search, Memory
- JSON serialization/deserialization for API transport
- 28 validation rules ensuring configuration integrity
- 4 configuration presets: Baseline, Basic RAG, Advanced RAG, Full Stack
- **47 unit tests** with 100% coverage

**Run History System** (`src/memory/run_history.py`)
- Tracks last 8 runs with query, configuration, response, and metrics
- Thread-safe JSON file storage with atomic writes
- Search by query text, technique, or model
- Export/import functionality
- **52 unit tests** with 100% coverage

**Modular Pipeline** (`src/core/modular_pipeline.py`)
- Abstract base class `ContextEngineeringModule` for all techniques
- 6 stub modules ready for Phase 3+ implementation
- Pipeline orchestrator with metric aggregation
- **15 unit tests** with 100% coverage

**API Endpoints** (`src/api/endpoints.py`)
- 9 new endpoints for configuration and run management:
  - `/api/config/presets` - Get configuration presets
  - `/api/config/default` - Get default configuration
  - `/api/config/validate` - Validate configurations
  - `/api/runs` - Get recent runs with filters
  - `/api/runs/{run_id}` - Get specific run
  - `/api/runs/compare` - Compare multiple runs
  - `/api/runs/stats` - Get history statistics
  - Enhanced `/api/chat` endpoint with configuration support

### ✅ Frontend Implementation

**Configuration Panel** (`ConfigurationPanel.tsx`)
- Two-tab interface: Simple (toggles) + Advanced (detailed settings)
- 6 technique toggle switches with validation feedback
- Preset selector with 4 presets
- Collapsible panel with localStorage persistence

**Run History & Comparison** (`RunHistory.tsx`, `RunComparison.tsx`)
- Displays last 8 runs with query, timestamp, model, and active techniques
- Multi-select for comparison (up to 3 runs)
- Filter by query text
- Side-by-side comparison modal with metric deltas
- Export to JSON functionality

**Metrics Page Transformation** (`Metrics.tsx`)
- Changed from "Phase Comparison" to "Run Comparison"
- Run selector with multi-select checkboxes
- Filters: date range, query text, enabled techniques
- 5 chart types: Latency, Token Usage, Relevance, Accuracy, Technique Impact
- Metrics summary table with best/worst highlighting

### 🎯 Key Features

**Experimentation Workflow:**
1. **Configure** → Toggle techniques, adjust parameters, or select presets
2. **Run** → Execute query with current configuration (automatically saved)
3. **Store** → Last 8 runs kept in persistent history
4. **Compare** → Select multiple runs for side-by-side analysis
5. **Analyze** → View metric deltas and technique impact
6. **Iterate** → Refine configuration based on insights

**Example Use Case:**
- Run 1: Baseline (no techniques) → Accuracy: 0.85
- Run 2: +RAG enabled → Accuracy: 0.95 (+10%)
- Run 3: +RAG +Compression → Accuracy: 0.93, Tokens: -22%

### 📚 Documentation
- **[PHASE2_COMPLETE.md](PHASE2_COMPLETE.md)** - Implementation completion report
- **[docs/PHASE2_API_DOCUMENTATION.md](docs/PHASE2_API_DOCUMENTATION.md)** - Complete API reference
- **[docs/PHASE2_QUICKSTART.md](docs/PHASE2_QUICKSTART.md)** - Quick start guide
- **[docs/phase_summaries/phase2_completion_summary.md](docs/phase_summaries/phase2_completion_summary.md)** - Detailed summary

## 🔮 Next Steps: Phase 3 - RAG Module Implementation

**Implementing the first context engineering technique!**

Phase 3 will implement RAG (Retrieval-Augmented Generation) as the first pluggable technique module:
- Set up ChromaDB vector database
- Implement document ingestion pipeline
- Create RAG retrieval module extending `ContextEngineeringModule`
- Add document upload UI in frontend
- **Measure real context engineering gains**: First meaningful metrics improvement over baseline!

## 🤝 Contributing

This is a research and demonstration project. Contributions are welcome:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and benchmarks
5. Submit a pull request

## 📝 License

[MIT License](LICENSE)

## 🙏 Acknowledgments

- Google ADK team
- Ollama project
- ChromaDB
- Sentence-Transformers
- FastAPI

---

## 🧪 Advanced Testing

### Testing Phase 2 API Endpoints

**Check API Health:**
```bash
curl http://localhost:8000/
# Returns: {"status": "healthy", "phase": "Phase 2 - Modular Pipeline Infrastructure", ...}
```

**Configuration Endpoints:**
```bash
# Get default configuration
curl http://localhost:8000/api/config/default

# Get all presets
curl http://localhost:8000/api/config/presets

# Get specific preset
curl http://localhost:8000/api/config/presets/basic_rag
curl http://localhost:8000/api/config/presets/full_stack

# Validate configuration
curl -X POST http://localhost:8000/api/config/validate \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "rag": {"enabled": true, "top_k": 5, "chunk_size": 512},
      "compression": {"enabled": false}
    }
  }'
```

**Chat with Configuration:**
```bash
# Basic chat (baseline)
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is machine learning?",
    "include_thinking": true
  }'

# Chat with RAG enabled
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is machine learning?",
    "include_thinking": true,
    "config": {
      "rag": {"enabled": true, "top_k": 5}
    }
  }'
```

**Run History Endpoints:**
```bash
# Get recent runs
curl http://localhost:8000/api/runs

# Get runs with query filter
curl http://localhost:8000/api/runs?query=machine+learning

# Get runs by technique
curl http://localhost:8000/api/runs?technique=rag

# Get specific run by ID
curl http://localhost:8000/api/runs/{run_id}

# Get run history statistics
curl http://localhost:8000/api/runs/stats

# Compare multiple runs
curl -X POST http://localhost:8000/api/runs/compare \
  -H "Content-Type: application/json" \
  -d '{
    "run_ids": ["run-id-1", "run-id-2", "run-id-3"]
  }'

# Clear run history
curl -X DELETE http://localhost:8000/api/runs
```

**Example Experimentation Workflow:**
```bash
# 1. Get baseline configuration
CONFIG_BASELINE=$(curl -s http://localhost:8000/api/config/presets/baseline)

# 2. Run query with baseline
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Explain RAG\", \"config\": $CONFIG_BASELINE}"

# 3. Get RAG configuration
CONFIG_RAG=$(curl -s http://localhost:8000/api/config/presets/basic_rag)

# 4. Run same query with RAG
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Explain RAG\", \"config\": $CONFIG_RAG}"

# 5. Get run history
curl http://localhost:8000/api/runs

# 6. Compare runs (use actual run IDs from step 5)
curl -X POST http://localhost:8000/api/runs/compare \
  -H "Content-Type: application/json" \
  -d '{"run_ids": ["<baseline-run-id>", "<rag-run-id>"]}'
```

For complete API documentation, see [docs/PHASE2_API_DOCUMENTATION.md](docs/PHASE2_API_DOCUMENTATION.md).

### Testing Individual Tools

**Calculator Tool:**
```bash
echo "What is 123 divided by 4?" | adk run context_engineering_agent
# Expected: Uses calculate tool, returns 30.75
```

**Word Counter Tool:**
```bash
echo "Count the words in: The quick brown fox jumps over the lazy dog" | adk run context_engineering_agent
# Expected: Uses count_words tool, returns 9 words
```

**Time Tool:**
```bash
echo "What's the current time in Asia/Tokyo?" | adk run context_engineering_agent
# Expected: Uses get_current_time tool, returns current JST time
```

**Text Analysis Tool:**
```bash
echo "Analyze this text: Python is an amazing programming language" | adk run context_engineering_agent
# Expected: Uses analyze_text tool, returns character count, word count, etc.
```

### Automated Test Suite

Run all tool tests automatically:
```bash
chmod +x scripts/test_adk_agent.sh
./scripts/test_adk_agent.sh
```

## 🔧 Troubleshooting

### Issue: "Command not found: adk"
**Solution:** Make sure Google ADK is installed:
```bash
pip install google-adk
adk --version  # Should show v1.17.0
```

### Issue: "Model not found: qwen3:4b"
**Solution:** Download the model:
```bash
ollama pull qwen3:4b
ollama list  # Verify it's downloaded
```

### Issue: "Connection refused to Ollama"
**Solution:** Ensure Ollama is running:
```bash
# Check if Ollama is running
ps aux | grep ollama

# If not, start it:
ollama serve
```

### Issue: Agent responds slowly
**Expected:** First response takes ~30-45 seconds (model reasoning + tool calling).
Subsequent responses are similar. This is normal for a 4B parameter model.

### Issue: "Directory 'context_engineering_agent' does not exist"
**Solution:** Make sure you're in the project root directory:
```bash
cd ADK-ContextEngineering
ls context_engineering_agent/  # Should show agent.py and __init__.py
```

---

**Note**: This project uses local models for zero-cost experimentation. All metrics are reproducible on consumer hardware.

*Last Updated: Phase 2 Complete - Modular Platform Infrastructure with Configuration System, Run History, and Comparison Framework - 2025-11-05*
