/**
 * Configuration types for Context Engineering techniques
 * 
 * These types mirror the Python backend configuration system defined in
 * src/core/context_config.py
 */

export interface NaiveRAGConfig {
  enabled: boolean
  chunk_size: number
  chunk_overlap: number
  top_k: number
  similarity_threshold: number
  embedding_model: string
}

export interface RAGToolConfig {
  enabled: boolean
  chunk_size: number
  chunk_overlap: number
  top_k: number
  similarity_threshold: number
  embedding_model: string
  tool_name: string
  tool_description: string
}

export interface CompressionConfig {
  enabled: boolean
  compression_ratio: number
  preserve_entities: boolean
  preserve_questions: boolean
  max_compressed_tokens: number
}

export interface RerankingConfig {
  enabled: boolean
  reranker_model: string
  top_n_after_rerank: number
  rerank_threshold: number
}

export interface CachingConfig {
  enabled: boolean
  similarity_threshold: number
  max_cache_size: number
  ttl_seconds: number
}

export interface HybridSearchConfig {
  enabled: boolean
  bm25_weight: number
  vector_weight: number
  top_k_per_method: number
}

export interface MemoryConfig {
  enabled: boolean
  max_conversation_turns: number
  include_summaries: boolean
  summary_trigger_turns: number
}

export interface ContextEngineeringConfig {
  naive_rag: NaiveRAGConfig
  rag_tool: RAGToolConfig
  compression: CompressionConfig
  reranking: RerankingConfig
  caching: CachingConfig
  hybrid_search: HybridSearchConfig
  memory: MemoryConfig
  model: string
  max_context_tokens: number
  temperature: number
}

export type ConfigPreset = 'baseline' | 'basic_rag' | 'advanced_rag' | 'full_stack'

export interface ConfigPresetInfo {
  name: string
  value: ConfigPreset
  description: string
  enabled_techniques: string[]
}

export interface ConfigValidationResponse {
  valid: boolean
  errors: string[]
}

export interface ConfigPresetsResponse {
  presets: Record<string, ContextEngineeringConfig>
  preset_info: Record<string, ConfigPresetInfo>
}

// Default configuration factory
export const createDefaultConfig = (): ContextEngineeringConfig => ({
  naive_rag: {
    enabled: false,
    chunk_size: 512,
    chunk_overlap: 50,
    top_k: 5,
    similarity_threshold: 0.75,
    embedding_model: 'sentence-transformers/all-MiniLM-L6-v2',
  },
  rag_tool: {
    enabled: false,
    chunk_size: 512,
    chunk_overlap: 50,
    top_k: 5,
    similarity_threshold: 0.75,
    embedding_model: 'sentence-transformers/all-MiniLM-L6-v2',
    tool_name: 'search_knowledge_base',
    tool_description: 'Search the knowledge base for relevant information about a specific topic or question',
  },
  compression: {
    enabled: false,
    compression_ratio: 0.5,
    preserve_entities: true,
    preserve_questions: true,
    max_compressed_tokens: 2048,
  },
  reranking: {
    enabled: false,
    reranker_model: 'cross-encoder/ms-marco-MiniLM-L-6-v2',
    top_n_after_rerank: 3,
    rerank_threshold: 0.6,
  },
  caching: {
    enabled: false,
    similarity_threshold: 0.95,
    max_cache_size: 1000,
    ttl_seconds: 3600,
  },
  hybrid_search: {
    enabled: false,
    bm25_weight: 0.3,
    vector_weight: 0.7,
    top_k_per_method: 10,
  },
  memory: {
    enabled: false,
    max_conversation_turns: 10,
    include_summaries: true,
    summary_trigger_turns: 5,
  },
  model: 'qwen2.5:7b',
  max_context_tokens: 4096,
  temperature: 0.7,
})

// Technique display names
export const TECHNIQUE_NAMES: Record<string, string> = {
  naive_rag: 'Naive RAG',
  rag_tool: 'RAG-as-tool',
  compression: 'Compression',
  reranking: 'Reranking',
  caching: 'Caching',
  hybrid_search: 'Hybrid Search',
  memory: 'Memory',
}

// Technique descriptions
export const TECHNIQUE_DESCRIPTIONS: Record<string, string> = {
  naive_rag: 'Naive RAG - Automatically retrieve and inject relevant documents into context before every LLM call',
  rag_tool: 'RAG-as-tool - Provide the LLM with a retrieval tool it can choose to invoke when needed',
  compression: 'Context Compression - Reduce context size while preserving key information',
  reranking: 'Document Reranking - Reorder retrieved documents for better relevance',
  caching: 'Semantic Caching - Cache similar queries to reduce latency and cost',
  hybrid_search: 'Hybrid Search - Combine BM25 and vector search for better retrieval',
  memory: 'Conversation Memory - Maintain context across multiple turns',
}

