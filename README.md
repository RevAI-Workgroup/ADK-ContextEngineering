# 🎯 Context Engineering Sandbox

> A demonstration project showcasing the progressive gains of context engineering techniques in LLM applications using Google ADK with local Ollama models.

## 📋 Project Overview

This project implements a comprehensive exploration of context engineering through 7 progressive phases, measuring the impact of each technique on:
- **Effectiveness**: Answer accuracy, relevance, hallucination rate
- **Efficiency**: Latency, token usage, cost
- **Scalability**: Throughput, memory usage

## 🚀 Technology Stack

- **LLM Framework**: Google ADK (Agentic Development Kit)
- **Local LLM**: Ollama with Qwen2.5 (configurable)
- **Vector Database**: ChromaDB (local, persistent)
- **Embeddings**: sentence-transformers (local)
- **API Framework**: FastAPI
- **Language**: Python 3.11+

## 📊 Project Status

**Current Phase**: Phase 0 - Foundation & Benchmarking ✅ **COMPLETE**

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

- ✅ **Phase 0**: Foundation & Benchmarking
- ⏳ **Phase 1**: MVP Agent with Google ADK
- ⏳ **Phase 2**: Basic RAG Implementation
- ⏳ **Phase 3**: Advanced Retrieval Techniques
- ⏳ **Phase 4**: Memory & State Management
- ⏳ **Phase 5**: Context Compression & Optimization
- ⏳ **Phase 6**: Advanced Context Engineering
- ⏳ **Phase 7**: System Integration & Optimization

## 🏗️ Project Structure

```
context-engineering-sandbox/
├── src/
│   ├── core/              # Core configuration and utilities
│   ├── evaluation/        # Metrics and benchmarking framework
│   ├── retrieval/         # Vector search and RAG (Phase 2+)
│   ├── memory/            # Conversation memory (Phase 4+)
│   ├── compression/       # Context compression (Phase 5+)
│   ├── advanced/          # Graph RAG, routing (Phase 6+)
│   └── api/               # FastAPI endpoints (Phase 1+)
├── configs/               # YAML configuration files
├── data/
│   ├── test_sets/         # Benchmark datasets
│   └── knowledge_base/    # Documents for RAG
├── scripts/               # Utility scripts
├── docs/                  # Documentation
└── tests/                 # Test suites
```

## 🚀 Quick Start

### 1. Setup Environment

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

### 2. Generate Benchmark Datasets

```bash
python scripts/create_benchmarks.py
```

### 3. Run Baseline Evaluation

```bash
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

## 🔬 Current Phase: Phase 0

Phase 0 establishes the foundation:

### ✅ Completed
- Project structure initialization
- Configuration management system
- Comprehensive metrics collection framework
- Benchmark dataset generation (15 baseline + 3 RAG tests)
- Evaluation orchestrator with A/B testing
- Baseline metrics measurement

### 📊 Key Findings
- Baseline ROUGE-1 F1: 0.3149 (simple echo system)
- Relevance score: 0.5698 (keyword-based)
- Hallucination rate: 0.0422 (heuristic detection)

## 🔮 Next Steps: Phase 1

Phase 1 will integrate Google ADK:
- Install and configure Google ADK
- Set up Ollama with Qwen2.5
- Create ADK agent wrapper
- Implement basic tool calling
- Build FastAPI endpoints
- Re-run evaluation and compare with Phase 0

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

**Note**: This project uses local models for zero-cost experimentation. All metrics are reproducible on consumer hardware.

*Last Updated: Phase 0 Complete*
