# Context Engineering Sandbox - Project Overview

## Purpose
This project demonstrates the progressive gains of context engineering techniques in LLM applications using Google ADK with Ollama (local LLMs).

## Core Objective
Build a measurable, experimental sandbox where each phase adds a new context engineering technique and quantifies its impact on:
- **Effectiveness**: Answer accuracy, relevance, hallucination rate
- **Efficiency**: Latency, token usage, cost
- **Scalability**: Throughput, memory usage

## Technology Stack
- **LLM Framework**: Google ADK (Agentic Development Kit)
- **Local LLM**: Ollama with Qwen2.5 (default, configurable)
- **Vector Database**: ChromaDB (local, persistent)
- **Embeddings**: sentence-transformers (local)
- **API Framework**: FastAPI
- **Language**: Python 3.11+

## Development Approach
- **AI-Driven Development**: Using Claude Code / Cursor
- **Metrics-First**: Every change must be measured
- **Incremental**: Each phase builds on previous work
- **Documented**: Comprehensive documentation at each step

## Project Phases

### Phase 0: Foundation (Current)
- Evaluation framework
- Baseline metrics
- Benchmark datasets

### Phase 1: MVP Agent
- Google ADK integration
- Basic tool calling
- FastAPI endpoints

### Phase 2: Basic RAG
- Vector database setup
- Document chunking
- Similarity search

### Phase 3: Advanced Retrieval
- Hybrid search (vector + BM25)
- Reranking
- Query enhancement

### Phase 4: Memory & State
- Conversation memory
- Semantic caching
- State management

### Phase 5: Compression
- Prompt compression
- Context filtering
- Token optimization

### Phase 6: Advanced Techniques
- Graph RAG
- Adaptive chunking
- Query routing

### Phase 7: Integration
- Full system integration
- Production optimization
- Final benchmarks

## Key Principles
1. **Measure Everything**: Baseline → Change → Measure → Document
2. **No Hardcoding**: Use configuration files
3. **Test-Driven**: Write tests before implementation
4. **Modular Design**: Single responsibility, dependency injection
5. **Documentation**: Keep .context/ files updated for AI assistants

## Current Status
- **Phase**: 0 - Foundation & Benchmarking
- **Next Step**: Complete baseline evaluation
- **Blockers**: None

## Quick Start
```bash
# Setup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create benchmarks
python scripts/create_benchmarks.py

# Run baseline evaluation
python scripts/run_evaluation.py

# Start API (once Phase 1 is complete)
uvicorn src.api.main:app --reload
```

## Important Files
- `BACKLOG.md`: Detailed implementation plan
- `configs/`: YAML configuration files
- `src/evaluation/`: Metrics and evaluation framework
- `data/test_sets/`: Benchmark datasets
- `.context/`: AI assistant context (this directory)

## Metrics Tracking
See `docs/phase_summaries/` for phase-by-phase metrics comparison.

---
*Last Updated: Phase 0 - Initial Setup*

