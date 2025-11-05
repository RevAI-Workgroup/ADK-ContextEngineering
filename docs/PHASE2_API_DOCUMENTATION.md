# Phase 2 API Documentation

## Overview

Phase 2 introduces a modular platform infrastructure for context engineering experimentation. This document describes the new API endpoints and configuration schema that enable dynamic technique toggling and run comparison.

---

## Configuration System

### Configuration Schema

The context engineering configuration consists of multiple technique configurations that can be independently enabled/disabled:

```json
{
  "model": "qwen2.5:7b",
  "temperature": 0.7,
  "max_tokens": 2000,
  "rag": {
    "enabled": false,
    "chunk_size": 512,
    "chunk_overlap": 50,
    "top_k": 5,
    "similarity_threshold": 0.7,
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2"
  },
  "compression": {
    "enabled": false,
    "compression_ratio": 0.7,
    "method": "extractive",
    "preserve_questions": true,
    "min_chunk_size": 100
  },
  "reranking": {
    "enabled": false,
    "reranker_model": "cross-encoder/ms-marco-MiniLM-L-6-v2",
    "top_n_after_rerank": 5,
    "use_diversity": false
  },
  "caching": {
    "enabled": false,
    "ttl_seconds": 3600,
    "similarity_threshold": 0.95,
    "max_cache_size": 1000
  },
  "hybrid_search": {
    "enabled": false,
    "bm25_weight": 0.3,
    "vector_weight": 0.7,
    "fusion_method": "weighted_sum"
  },
  "memory": {
    "enabled": false,
    "max_conversation_turns": 10,
    "summarization_enabled": true,
    "window_size": 5
  }
}
```

### Configuration Presets

Four presets are available for quick configuration:

1. **baseline**: All techniques disabled
2. **basic_rag**: Only RAG enabled
3. **advanced_rag**: RAG + Reranking + Hybrid Search
4. **full_stack**: All techniques enabled

---

## API Endpoints

### Configuration Endpoints

#### `GET /api/config/presets`

Get all available configuration presets.

**Response:**
```json
{
  "presets": {
    "baseline": { /* config object */ },
    "basic_rag": { /* config object */ },
    "advanced_rag": { /* config object */ },
    "full_stack": { /* config object */ }
  }
}
```

**Status Codes:**
- `200 OK`: Success

---

#### `GET /api/config/default`

Get the default configuration (baseline).

**Response:**
```json
{
  "config": { /* default config object */ }
}
```

**Status Codes:**
- `200 OK`: Success

---

#### `POST /api/config/validate`

Validate a configuration object.

**Request Body:**
```json
{
  "config": { /* configuration to validate */ }
}
```

**Response (valid):**
```json
{
  "valid": true,
  "errors": []
}
```

**Response (invalid):**
```json
{
  "valid": false,
  "errors": [
    "RAG chunk_size must be positive",
    "Reranking requires RAG to be enabled"
  ]
}
```

**Status Codes:**
- `200 OK`: Validation completed
- `400 Bad Request`: Invalid request body

---

### Run History Endpoints

#### `GET /api/runs`

Get recent runs from history.

**Query Parameters:**
- `limit` (optional, integer): Maximum number of runs to return (default: 8)
- `query` (optional, string): Filter runs by query text (case-insensitive substring match)

**Example:** `/api/runs?limit=5&query=RAG`

**Response:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "query": "What is RAG?",
    "config": { /* full config */ },
    "response": "RAG stands for...",
    "metrics": {
      "latency_ms": 1234.5,
      "token_count": 500,
      "relevance_score": 0.85,
      "accuracy": 0.92
    },
    "timestamp": "2025-11-05T10:30:00Z",
    "model": "qwen2.5:7b",
    "duration_ms": 1234.5,
    "enabled_techniques": ["rag", "compression"]
  }
]
```

**Status Codes:**
- `200 OK`: Success
- `400 Bad Request`: Invalid query parameters

---

#### `GET /api/runs/{run_id}`

Get a specific run by ID.

**Path Parameters:**
- `run_id` (string): UUID of the run

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "query": "What is RAG?",
  "config": { /* full config */ },
  "response": "RAG stands for...",
  "metrics": { /* metrics */ },
  "timestamp": "2025-11-05T10:30:00Z",
  "model": "qwen2.5:7b",
  "duration_ms": 1234.5,
  "enabled_techniques": ["rag"]
}
```

**Status Codes:**
- `200 OK`: Success
- `404 Not Found`: Run not found

---

#### `POST /api/runs/clear`

Clear all run history.

**Request Body:** None

**Response:**
```json
{
  "success": true,
  "message": "Run history cleared"
}
```

**Status Codes:**
- `200 OK`: Success

---

#### `GET /api/runs/compare`

Compare multiple runs.

**Query Parameters:**
- `run_ids` (required, array): Array of run IDs to compare (provide multiple `run_ids` parameters)

**Example:** `/api/runs/compare?run_ids=id1&run_ids=id2&run_ids=id3`

**Response:**
```json
{
  "runs": [ /* array of RunRecord objects */ ],
  "query": "What is RAG?",
  "metrics_comparison": {
    "latency_ms": {
      "values": [1234, 987, 1456],
      "best_index": 1,
      "worst_index": 2,
      "differences": [0, -247, 222]
    },
    "accuracy": {
      "values": [0.85, 0.92, 0.88],
      "best_index": 1,
      "worst_index": 0,
      "differences": [0, 0.07, 0.03]
    }
  },
  "config_comparison": {
    "differences": [
      {
        "technique": "rag",
        "parameter": "top_k",
        "values": [5, 10, 5]
      }
    ],
    "enabled_techniques": [
      ["rag"],
      ["rag", "compression"],
      ["rag"]
    ]
  },
  "timestamp": "2025-11-05T10:30:00Z"
}
```

**Status Codes:**
- `200 OK`: Success
- `400 Bad Request`: Invalid or missing run_ids
- `404 Not Found`: One or more runs not found

---

#### `GET /api/runs/stats`

Get run history statistics.

**Response:**
```json
{
  "total_runs": 25,
  "models_used": ["qwen2.5:7b", "qwen2.5:3b"],
  "techniques_used": ["rag", "compression", "reranking"],
  "date_range": {
    "earliest": "2025-11-01T08:00:00Z",
    "latest": "2025-11-05T10:30:00Z"
  },
  "average_duration_ms": 1523.7
}
```

**Status Codes:**
- `200 OK`: Success

---

#### `GET /api/runs/export`

Export run history as JSON file.

**Response:**
- Content-Type: `application/json`
- Content-Disposition: `attachment; filename="run_history_YYYY-MM-DD.json"`
- Body: JSON array of all runs

**Status Codes:**
- `200 OK`: Success

---

### Chat Endpoint Updates

#### `POST /api/chat`

Process a query with specified configuration.

**Request Body:**
```json
{
  "query": "What is RAG?",
  "config": { /* optional configuration object */ },
  "stream": false
}
```

**Response:**
```json
{
  "query": "What is RAG?",
  "response": "RAG stands for Retrieval-Augmented Generation...",
  "thinking": "Let me break this down...",
  "tool_outputs": [],
  "metrics": {
    "latency_ms": 1234.5,
    "token_count": 500,
    "retrieval_time_ms": 45.2,
    "generation_time_ms": 1189.3
  },
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "config_used": { /* actual config used */ },
  "enabled_techniques": ["rag"]
}
```

**Status Codes:**
- `200 OK`: Success
- `400 Bad Request`: Invalid request body or configuration
- `500 Internal Server Error`: Processing error

---

## Configuration Validation Rules

The following validation rules are enforced:

### RAG Configuration
- `chunk_size` must be > 0
- `chunk_overlap` must be >= 0 and < `chunk_size`
- `top_k` must be > 0
- `similarity_threshold` must be between 0 and 1

### Compression Configuration
- `compression_ratio` must be between 0 and 1
- `min_chunk_size` must be > 0

### Reranking Configuration
- Requires `rag.enabled` to be `true`
- `top_n_after_rerank` must be <= `rag.top_k`

### Caching Configuration
- `ttl_seconds` must be > 0
- `similarity_threshold` must be between 0 and 1
- `max_cache_size` must be > 0

### Hybrid Search Configuration
- Requires `rag.enabled` to be `true`
- `bm25_weight` + `vector_weight` must equal 1.0

### Memory Configuration
- `max_conversation_turns` must be > 0
- `window_size` must be > 0 and <= `max_conversation_turns`

### General Configuration
- `temperature` must be between 0 and 2
- `max_tokens` must be > 0
- `model` must be non-empty string

---

## Error Responses

All endpoints return errors in the following format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

Common status codes:
- `400 Bad Request`: Invalid input or validation error
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server-side error

---

## Data Types

### RunRecord

```typescript
interface RunRecord {
  id: string                          // UUID
  query: string                       // User query
  config: ContextEngineeringConfig   // Configuration used
  response: string                    // Agent response
  metrics: Record<string, any>       // Performance metrics
  timestamp: string                   // ISO 8601 timestamp
  model: string                       // Model identifier
  duration_ms: number                // Total duration
  enabled_techniques: string[]       // Active techniques
}
```

### ContextEngineeringConfig

See [Configuration Schema](#configuration-schema) section above.

---

## Usage Examples

### Example 1: Run with basic RAG

```bash
# Get basic RAG preset
curl http://localhost:8000/api/config/presets

# Process query with basic RAG
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is context engineering?",
    "config": {
      "rag": { "enabled": true }
    }
  }'
```

### Example 2: Compare runs

```bash
# Get recent runs
curl http://localhost:8000/api/runs?limit=5

# Compare specific runs
curl "http://localhost:8000/api/runs/compare?run_ids=id1&run_ids=id2"
```

### Example 3: Custom configuration

```bash
# Validate custom config
curl -X POST http://localhost:8000/api/config/validate \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "rag": {
        "enabled": true,
        "top_k": 10
      },
      "compression": {
        "enabled": true,
        "compression_ratio": 0.8
      }
    }
  }'

# Use custom config
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Explain RAG",
    "config": {
      "rag": { "enabled": true, "top_k": 10 },
      "compression": { "enabled": true, "compression_ratio": 0.8 }
    }
  }'
```

---

## Integration Notes

### Frontend Integration

The frontend uses the following services:

- `configService.ts`: Handles configuration endpoints
- `runHistoryService.ts`: Handles run history endpoints
- `agentService.ts`: Handles chat endpoint

### State Management

- Configuration state is managed in `ChatContext`
- Selected runs for comparison are managed in `useMetrics` hook
- Run history is automatically refreshed after each query

### Caching Strategy

- Frontend caches configuration presets in localStorage
- Run history is cached in memory and refreshed on demand
- No caching for chat responses (always fresh)

---

## Future Enhancements

Planned for Phase 3+:

1. **Batch Processing**: `/api/batch` endpoint for processing multiple queries
2. **Run Tagging**: Add tags to runs for better organization
3. **Run Notes**: Add user notes/annotations to runs
4. **Export Formats**: Support CSV, Excel export formats
5. **Advanced Filtering**: Filter by date range, metrics thresholds
6. **Comparison Templates**: Save and reuse comparison configurations
7. **Real-time Metrics**: WebSocket endpoint for streaming metrics

---

## Version History

- **v1.0.0** (2025-11-05): Initial Phase 2 API release
  - Configuration management endpoints
  - Run history management endpoints
  - Run comparison endpoint
  - Configuration validation

---

## Support

For issues or questions:
- Check the main README.md for setup instructions
- Review test files in `tests/unit/` for usage examples
- Consult BACKLOG.md for implementation details

