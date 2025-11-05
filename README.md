# 🎯 Context Engineering Sandbox

**Experiment with context engineering techniques for LLMs and measure their real impact.**

A modular experimentation platform that lets you toggle different context engineering techniques (RAG, compression, caching, etc.) on/off, run the same query with different configurations, and compare results side-by-side to see which techniques actually improve your LLM's performance.

Built with Google ADK, local Ollama models, React, and FastAPI.

---

## ⚡ Quick Start (5 Minutes)

### Prerequisites
- Python 3.11+
- [Ollama](https://ollama.com) installed and running

### Install & Run

```bash
# 1. Install Ollama (if not already installed)
brew install ollama  # macOS
# Or download from https://ollama.com for other platforms

# 2. Download the LLM model
ollama pull qwen3:4b  # 2.5 GB, takes 1-2 minutes

# 3. Clone and setup
git clone https://github.com/RevAI-Workgroup/ADK-ContextEngineering.git
cd ADK-ContextEngineering
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 4. Start the application
./start-dev.sh  # Starts both backend and frontend

# 5. Open your browser
# Visit http://localhost:5173
```

**That's it!** You now have a running LLM experimentation platform.

---

## 🎯 What You Can Do

### 1. **Chat with an LLM Agent**
- Interactive chat interface with AI agent
- Built-in tools: calculator, text analysis, current time, word counter
- Real-time streaming responses
- See the agent's thinking process

### 2. **Toggle Context Engineering Techniques**
Enable/disable different techniques to improve LLM responses:
- **RAG** (Retrieval-Augmented Generation) - Retrieve relevant context
- **Compression** - Reduce token usage while maintaining quality
- **Reranking** - Improve retrieval relevance
- **Caching** - Speed up repeated queries
- **Hybrid Search** - Combine keyword and semantic search
- **Memory** - Maintain conversation context

### 3. **Compare Configurations**
- Run the same query with different technique combinations
- See side-by-side comparisons of responses
- View metric deltas: accuracy, latency, token usage
- Identify which techniques provide the most value

### 4. **Measure Real Impact**
Track comprehensive metrics:
- **Accuracy**: ROUGE scores, relevance scores
- **Efficiency**: Latency (ms), token usage, cost
- **Quality**: Hallucination rate, coherence

### 5. **Experiment Systematically**
1. Configure techniques (Simple or Advanced mode)
2. Run query → Automatically saved to history
3. Adjust configuration
4. Run same query again
5. Compare results in Metrics dashboard
6. Iterate and optimize

---

## 💡 Usage Guide

### Basic Usage: Chat

1. **Start the application** (see Quick Start above)
2. **Navigate to Chat page** at http://localhost:5173
3. **Type a question** and press Enter
4. **See the response** with thinking process and tool usage

**Example queries:**
```
What is 15 multiplied by 7?
Analyze this text: The quick brown fox jumps
What time is it in Tokyo?
Explain how machine learning works
```

### Advanced Usage: Configuration & Comparison

#### **Step 1: Configure Techniques**

On the Chat page:
1. Click **"⚙️ Configuration"** button
2. **Simple Tab**: Toggle techniques on/off, select a preset
3. **Advanced Tab**: Fine-tune parameters (chunk size, top-k, thresholds, etc.)

**Available Presets:**
- **Baseline**: No techniques (pure LLM)
- **Basic RAG**: RAG only
- **Advanced RAG**: RAG + Reranking + Hybrid Search
- **Full Stack**: All techniques enabled

#### **Step 2: Run Experiments**

1. Configure your first setup (e.g., Baseline)
2. Ask a question: `"What is RAG?"`
3. Note the response quality and metrics
4. Change configuration (e.g., enable RAG)
5. Ask the **same question** again
6. Compare responses!

#### **Step 3: Compare Results**

**In Chat Page:**
- View last 8 runs in **Run History** sidebar
- Check boxes next to runs to compare
- Click **"Compare Selected"**
- See side-by-side comparison with metric deltas

**In Metrics Page:**
- Select multiple runs using checkboxes
- Filter by date, query text, or techniques
- View interactive charts:
  - Latency comparison
  - Token usage
  - Accuracy scores
  - Technique impact
- Export comparison data as JSON

#### **Step 4: Analyze & Iterate**

**Look for:**
- ✅ Which configuration has best accuracy?
- ✅ Which has lowest latency?
- ✅ What's the accuracy vs. efficiency trade-off?
- ✅ Are you over-engineering? (Do you need all techniques?)

**Example Results:**
```
Run 1: Baseline          → Accuracy: 0.85, Latency: 800ms
Run 2: +RAG              → Accuracy: 0.95 (+10%), Latency: 1200ms
Run 3: +RAG +Compression → Accuracy: 0.93 (-2%), Tokens: -22%, Latency: 1000ms

Conclusion: RAG improves accuracy significantly.
           Compression reduces tokens with minimal accuracy loss.
```

---

## 🚀 Running Options

### Option A: Full Stack (Recommended)

**Using the dev script:**
```bash
./start-dev.sh  # Starts backend + frontend with nice logging
```

**Using Docker:**
```bash
docker-compose -f docker/docker-compose.yml up --build
# Access at http://localhost
```

### Option B: Backend Only

```bash
./start_backend.sh
# Or manually:
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
# API docs at http://localhost:8000/docs
```

### Option C: CLI Mode (No Web UI)

```bash
# Interactive chat
adk run context_engineering_agent

# Single query
echo "What is 5 plus 3?" | adk run context_engineering_agent

# ADK's built-in web interface
adk web
```

### Option D: Frontend Only (for development)

```bash
cd frontend
pnpm install  # or: npm install
pnpm dev      # or: npm run dev
# Opens at http://localhost:5173
```

---

## 🔧 Configuration

### Technique Settings

All techniques can be configured via the web UI or directly through the API.

**Configuration Structure:**
```json
{
  "rag": {
    "enabled": true,
    "chunk_size": 512,
    "top_k": 5,
    "similarity_threshold": 0.7
  },
  "compression": {
    "enabled": true,
    "compression_ratio": 0.5,
    "method": "extractive"
  },
  "reranking": {
    "enabled": false,
    "model": "cross-encoder",
    "top_n": 3
  }
  // ... more techniques
}
```

### Environment Configuration

**YAML files in `configs/`:**
- `models.yaml` - LLM and embedding model settings
- `retrieval.yaml` - Vector search and chunking
- `evaluation.yaml` - Metrics and benchmarking

**Environment Variable Override:**
```bash
# Override any config value
export MODELS_OLLAMA_TIMEOUT=240
export MODELS_OLLAMA_BASE_URL=http://localhost:11434
```

---

## 🧪 Testing

### Test the Application

```bash
# Test Phase 1 tools (calculator, text analysis, etc.)
./scripts/test_adk_agent.sh

# Test Phase 2 backend (configuration, run history, pipeline)
pytest tests/unit/test_context_config.py -v
pytest tests/unit/test_run_history.py -v
pytest tests/unit/test_modular_pipeline.py -v

# Run all tests
pytest tests/ -v
```

### Test the API

```bash
# Check API health
curl http://localhost:8000/

# Get configuration presets
curl http://localhost:8000/api/config/presets

# Chat with baseline config
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is machine learning?"}'

# Get run history
curl http://localhost:8000/api/runs

# Compare runs
curl "http://localhost:8000/api/runs/compare?run_ids=run1,run2"
```

See [docs/PHASE2_API_DOCUMENTATION.md](docs/PHASE2_API_DOCUMENTATION.md) for complete API reference.

---

## 🏗️ Architecture

### Technology Stack

**Backend:**
- Google ADK v1.17.0 (Agentic Development Kit)
- FastAPI + Uvicorn (REST API + WebSocket)
- Ollama + Qwen3 4B (Local LLM - 2.5 GB)
- LiteLLM v1.72.6 (Model integration)
- Python 3.11+

**Frontend:**
- React 18 + TypeScript
- Vite (Build tool)
- Shadcn/UI (UI components)
- Recharts (Metrics visualization)
- Tailwind CSS

**Infrastructure:**
- ChromaDB (Vector database - planned for Phase 3)
- Docker + Docker Compose
- Local-first, zero-cost experimentation

### Project Structure

```
context-engineering-sandbox/
├── frontend/              # React Web UI
│   ├── src/
│   │   ├── components/   # UI components
│   │   ├── pages/        # Chat, Metrics, Home
│   │   ├── services/     # API clients
│   │   └── types/        # TypeScript types
│   └── package.json
├── src/                   # Backend Python
│   ├── api/              # FastAPI endpoints
│   ├── core/             # Configuration & pipeline
│   ├── memory/           # Run history
│   ├── evaluation/       # Metrics framework
│   ├── retrieval/        # RAG (Phase 3)
│   ├── compression/      # Compression (Phase 4)
│   └── advanced/         # Advanced techniques (Phase 6)
├── context_engineering_agent/  # ADK agent
├── configs/              # YAML configuration
├── data/
│   ├── test_sets/        # Benchmark datasets
│   └── run_history.json  # Persistent run storage
├── docker/               # Docker setup
├── scripts/              # Utility scripts
├── tests/                # Test suites
└── docs/                 # Documentation
```

---

## 📚 Documentation

### User Guides
- **[PHASE2_QUICKSTART.md](docs/PHASE2_QUICKSTART.md)** - Detailed quick start guide
- **[PHASE2_API_DOCUMENTATION.md](docs/PHASE2_API_DOCUMENTATION.md)** - Complete API reference

### Technical Documentation
- **[BACKLOG.md](BACKLOG.md)** - Project roadmap and implementation plan
- **[docs/phase_summaries/](docs/phase_summaries/)** - Phase completion reports
- **[PHASE2_COMPLETE.md](PHASE2_COMPLETE.md)** - Phase 2 implementation summary

### Development Progress

The project is built in progressive phases:

- ✅ **Phase 0**: Foundation & Benchmarking
- ✅ **Phase 1**: MVP Agent with Google ADK
- ✅ **Phase 1.5**: Web UI Development
- ✅ **Phase 2**: Modular Platform Infrastructure (Current - Completed Nov 2025)
- ⏳ **Phase 3**: RAG Module (Next)
- ⏳ **Phase 4**: Compression, Caching & Memory Modules
- ⏳ **Phase 5**: Reranking & Hybrid Search Modules
- ⏳ **Phase 6**: Advanced Techniques (Graph RAG, adaptive chunking)
- ⏳ **Phase 7**: System Integration & Optimization

**Current Status:** Modular platform complete with configuration system, run history, and comparison framework. Ready for technique implementations.

See [BACKLOG.md](BACKLOG.md) for detailed phase plans.

---

## 🔧 Troubleshooting

### "Command not found: adk"
```bash
pip install google-adk
adk --version  # Should show v1.17.0
```

### "Model not found: qwen3:4b"
```bash
ollama pull qwen3:4b
ollama list  # Verify it's downloaded
```

### "Connection refused to Ollama"
```bash
# Check if Ollama is running
ps aux | grep ollama

# If not, start it:
ollama serve
```

### Agent responds slowly
**Expected behavior.** First response takes ~30-45 seconds for a 4B parameter model. This is normal for local models.

### "Directory 'context_engineering_agent' does not exist"
```bash
# Make sure you're in the project root
cd ADK-ContextEngineering
ls context_engineering_agent/  # Should show agent.py
```

### Frontend won't start
```bash
# Install dependencies first
cd frontend
pnpm install  # or: npm install
pnpm dev
```

### Tests fail with "ModuleNotFoundError"
```bash
# Activate virtual environment first
source venv/bin/activate  # On Windows: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## 🤝 Contributing

This is a research and demonstration project. Contributions are welcome!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests: `pytest tests/ -v`
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

---

## 📝 License

[MIT License](LICENSE)

---

## 🙏 Acknowledgments

- [Google ADK](https://github.com/google/adk) - Agentic Development Kit
- [Ollama](https://ollama.com) - Local LLM runtime
- [Qwen](https://github.com/QwenLM/Qwen) - Open-source LLM
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Shadcn/UI](https://ui.shadcn.com/) - Beautiful UI components

---

## 📊 Project Metrics

**Current Baseline Performance** (Phase 0):

| Metric | Value |
|--------|-------|
| ROUGE-1 F1 | 0.3149 |
| ROUGE-2 F1 | 0.1598 |
| ROUGE-L F1 | 0.2509 |
| Relevance Score | 0.5698 |
| Hallucination Rate | 0.0422 |
| Latency | ~0ms (no RAG) |
| Tokens/Query | 29.27 |

**Goal:** Measure improvement as context engineering techniques are applied!

---

**Note:** This project uses local models for zero-cost experimentation. All metrics are reproducible on consumer hardware.

*Last Updated: Phase 2 Complete - Modular Platform Infrastructure - 2025-11-05*
