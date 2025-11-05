# Phase 2 Backend - Quick Start Guide

This guide shows you how to test the Phase 2 backend implementation.

## 🚀 Starting the Backend

### Option 1: Using the startup script
```bash
./start_backend.sh
```

### Option 2: Manual start
```bash
source venv/bin/activate
cd src/api
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: **http://localhost:8000**

---

## 📖 API Documentation

Once the backend is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 🧪 Testing the New Endpoints

### 1. Check API Health

```bash
curl http://localhost:8000/
```

Expected response:
```json
{
  "status": "healthy",
  "service": "Context Engineering Sandbox API",
  "version": "2.0.0",
  "phase": "Phase 2 - Modular Pipeline Infrastructure",
  "timestamp": "2025-11-04T..."
}
```

---

### 2. Configuration Endpoints

#### Get Default Configuration
```bash
curl http://localhost:8000/api/config/default
```

#### Get All Presets
```bash
curl http://localhost:8000/api/config/presets
```

#### Get Specific Preset
```bash
curl http://localhost:8000/api/config/presets/basic_rag
curl http://localhost:8000/api/config/presets/full_stack
```

#### Validate Configuration
```bash
curl -X POST http://localhost:8000/api/config/validate \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "rag": {"enabled": true, "top_k": 5},
      "compression": {"enabled": false}
    }
  }'
```

---

### 3. Chat with Configuration

#### Basic Chat (No Configuration)
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is 5 + 3?",
    "include_thinking": true
  }'
```

#### Chat with RAG Enabled
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is context engineering?",
    "config": {
      "rag": {
        "enabled": true,
        "top_k": 5,
        "chunk_size": 512
      }
    }
  }'
```

**Note**: RAG module is currently a stub, so it won't retrieve actual documents yet. But you'll see it in the pipeline metrics!

#### Chat with Multiple Techniques
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain neural networks",
    "config": {
      "rag": {"enabled": true},
      "compression": {"enabled": true, "compression_ratio": 0.7},
      "memory": {"enabled": true}
    }
  }'
```

Check the response for:
- `pipeline_metrics` - Shows execution time of each module
- `enabled_techniques` - Lists which techniques were active
- `pipeline_metadata` - Module-specific metadata

---

### 4. Run History Endpoints

**Note**: Run history is not automatically populated by chat endpoint yet. In Phase 2 frontend, we'll add logic to save runs.

#### Get Recent Runs
```bash
curl http://localhost:8000/api/runs
curl http://localhost:8000/api/runs?limit=5
```

#### Filter Runs by Query
```bash
curl "http://localhost:8000/api/runs?query=neural"
```

#### Filter by Technique
```bash
curl http://localhost:8000/api/runs?technique=rag
```

#### Get Specific Run
```bash
curl http://localhost:8000/api/runs/{run_id}
```

#### Get Run Statistics
```bash
curl http://localhost:8000/api/runs/stats
```

#### Compare Multiple Runs
```bash
curl "http://localhost:8000/api/runs/compare?run_ids=abc123,def456,ghi789"
```

#### Clear Run History
```bash
curl -X POST http://localhost:8000/api/runs/clear
```

---

## 🧪 Running Tests

### Unit Tests
```bash
source venv/bin/activate
python -m pytest tests/unit/test_modular_pipeline.py -v
```

Expected: **26 tests passed**

### Integration Tests
```bash
source venv/bin/activate
python scripts/test_phase2_api.py
```

Expected: All tests should pass with ✅ symbols

---

## 🔍 What to Look For

### In Chat Responses

When you send a message with configuration enabled, look for these fields:

```json
{
  "response": "...",
  "metrics": {
    "latency_ms": 1234.56,
    "pipeline_metrics": {
      "enabled_modules": ["rag", "compression"],
      "total_execution_time_ms": 0.52,
      "modules": {
        "rag": {
          "module_name": "RAG",
          "execution_time_ms": 0.31,
          "technique_specific": {
            "status": "stub",
            "retrieved_docs": 0
          }
        },
        "compression": {
          "module_name": "Compression",
          "execution_time_ms": 0.21,
          "technique_specific": {
            "status": "stub",
            "tokens_saved": 0
          }
        }
      }
    },
    "enabled_techniques": ["rag", "compression"]
  },
  "pipeline_metadata": {
    "rag_status": "stub - not yet implemented",
    "rag_config": {...},
    "compression_status": "stub - not yet implemented",
    "compression_config": {...}
  }
}
```

**Key Points:**
1. `enabled_techniques` shows which modules were active
2. `pipeline_metrics` shows execution time per module
3. `pipeline_metadata` contains module-specific information
4. Each stub module adds `"status": "stub"` to indicate it's not fully implemented

---

## 🎯 Testing Scenarios

### Scenario 1: Compare Baseline vs RAG
```bash
# Run 1: Baseline (no techniques)
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is Python?"}'

# Run 2: With RAG
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is Python?",
    "config": {"rag": {"enabled": true}}
  }'
```

Compare the `pipeline_metrics` to see the overhead (currently ~0ms for stubs).

### Scenario 2: Test All Presets
```bash
# Get all presets
PRESETS=$(curl -s http://localhost:8000/api/config/presets | jq -r '.preset_names[]')

# Test each preset
for preset in $PRESETS; do
  echo "Testing preset: $preset"
  CONFIG=$(curl -s http://localhost:8000/api/config/presets/$preset | jq '.config')
  curl -X POST http://localhost:8000/api/chat \
    -H "Content-Type: application/json" \
    -d "{\"message\": \"Test\", \"config\": $CONFIG}" | jq '.metrics.enabled_techniques'
done
```

### Scenario 3: Configuration Validation
```bash
# Valid config
curl -X POST http://localhost:8000/api/config/validate \
  -H "Content-Type: application/json" \
  -d '{"config": {"rag": {"enabled": true, "top_k": 5}}}'

# Invalid config (negative chunk_size)
curl -X POST http://localhost:8000/api/config/validate \
  -H "Content-Type: application/json" \
  -d '{"config": {"rag": {"enabled": true, "chunk_size": -100}}}'
```

---

## 🐛 Troubleshooting

### Backend Won't Start
1. Check if port 8000 is already in use:
   ```bash
   lsof -i :8000
   ```
2. Ensure virtual environment is activated:
   ```bash
   source venv/bin/activate
   ```
3. Check dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```

### No Response from API
1. Check backend is running: `curl http://localhost:8000/`
2. Check for errors in terminal where backend is running
3. Try restarting the backend

### Module Not Working
Remember: All modules are **stubs** in Phase 2. They:
- Accept configuration
- Pass through data unchanged
- Record metrics
- Add metadata

Real implementations come in:
- Phase 3: RAG Module
- Phase 4: Compression, Caching, Memory
- Phase 5: Reranking, Hybrid Search

---

## 📚 Next Steps

### For Backend Development:
1. Start implementing RAG module (Phase 3)
2. Add document upload endpoints
3. Integrate ChromaDB

### For Frontend Development:
1. Create Configuration Panel component
2. Build Run History sidebar
3. Implement Run Comparison modal
4. Add configuration persistence

### For Testing:
1. Add more unit tests for edge cases
2. Create integration tests for WebSocket
3. Add load testing for pipeline performance

---

## 📖 Additional Resources

- **Full API Docs**: http://localhost:8000/docs
- **Phase 2 Summary**: `docs/phase_summaries/phase2_backend_summary.md`
- **BACKLOG**: `BACKLOG.md` (Phase 2 section)
- **Module Code**: `src/core/modular_pipeline.py`
- **Tests**: `tests/unit/test_modular_pipeline.py`

---

## ✅ Verification Checklist

Before moving to frontend development, verify:

- [ ] Backend starts successfully
- [ ] Health check endpoint works
- [ ] All 4 config presets load correctly
- [ ] Configuration validation catches errors
- [ ] Chat endpoint accepts config parameter
- [ ] Pipeline metrics appear in response
- [ ] All 26 unit tests pass
- [ ] Integration tests pass
- [ ] Swagger docs accessible

---

**Questions or Issues?**
- Check logs in terminal where backend is running
- Review error messages in API responses
- Consult `docs/phase_summaries/phase2_backend_summary.md`

