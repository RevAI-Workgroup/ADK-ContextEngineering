# 🎯 Context Engineering Sandbox

> A demonstration project showcasing the progressive gains of context engineering techniques in LLM applications using Google ADK with local Ollama models.

## 📋 Project Overview

This project implements a comprehensive exploration of context engineering through 7 progressive phases, measuring the impact of each technique on:
- **Effectiveness**: Answer accuracy, relevance, hallucination rate
- **Efficiency**: Latency, token usage, cost
- **Scalability**: Throughput, memory usage

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

**Current Phase**: Phase 1.5 - Web UI Development ✅ **COMPLETE**

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
- ⏳ **Phase 2**: Basic RAG Implementation (Next - Context Engineering Begins!)
- ⏳ **Phase 3**: Advanced Retrieval Techniques
- ⏳ **Phase 4**: Memory & State Management
- ⏳ **Phase 5**: Context Compression & Optimization
- ⏳ **Phase 6**: Advanced Context Engineering
- ⏳ **Phase 7**: System Integration & Optimization

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

### 5. Run Tests (Optional)

**Manual Test Script:**
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

- **[BACKLOG.md](BACKLOG.md)** - Detailed implementation plan for all phases
- **[.context/](.context/)** - AI assistant context files
- **[docs/phase_summaries/](docs/phase_summaries/)** - Phase completion reports

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

## 🔮 Next Steps: Phase 2 - RAG Implementation

**This is where context engineering truly begins!**

Phase 2 will add the critical RAG retrieval tool:
- Set up ChromaDB vector database
- Create RAG retrieval tool
- Implement document ingestion pipeline
- Add document upload UI in frontend
- Integrate RAG with agent
- **Measure context engineering gains**: First meaningful metrics improvement!

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

*Last Updated: Phase 1.5 Complete - 2025-10-31*
