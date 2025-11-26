import { ToolCall } from './agent.types'

export type MessageRole = 'user' | 'assistant' | 'system'

export interface RetrievedDocument {
  text: string
  source: string
  similarity: number
  chunk_index?: number | string
  metadata?: Record<string, any>
}

export interface RAGMetadata {
  // Naive RAG metadata
  rag_status?: string
  rag_retrieved_docs?: number
  rag_sources?: string[]
  rag_avg_similarity?: number
  rag_error?: string
  rag_message?: string
  rag_documents?: RetrievedDocument[]

  // RAG-as-tool metadata
  rag_tool_status?: string
  rag_tool_name?: string
  rag_tool_calls?: number
  rag_tool_documents?: RetrievedDocument[]
}

export interface PipelineMetrics {
  total_execution_time_ms?: number
  modules?: Record<string, {
    execution_time_ms: number
    technique_specific?: Record<string, any>
    module_name?: string
    input_tokens?: number
    output_tokens?: number
  }>
}

export interface Message {
  id: string
  role: MessageRole
  content: string
  thinking?: string[]
  reasoning?: string  // For reasoning tokens from models like o1
  toolCalls?: ToolCall[]
  timestamp: string
  model?: string
  pipelineMetadata?: RAGMetadata
  pipelineMetrics?: PipelineMetrics
  metrics?: {
    latency_ms?: number
    enabled_techniques?: string[]
  }
}

// Data interfaces for each event type
export interface ThinkingEventData {
  message: string
}

export interface ToolCallEventData {
  // New structured format
  name?: string
  description?: string
  parameters?: Record<string, unknown> | unknown[]
  timestamp?: string
  // Legacy format for backward compatibility
  message?: string
}

export interface ToolResultEventData {
  name: string
  result: unknown
  timestamp?: string
}

export interface ResponseEventData {
  response: string
  thinking_steps?: string[]
  tool_calls?: ToolCall[]
}

// Token streaming event data
export interface TokenEventData {
  token: string
  cumulative_response: string
}

export interface ReasoningTokenEventData {
  token: string
  cumulative_reasoning: string
}

export interface CompleteEventData {
  model?: string
  reasoning_length?: number
  response_length?: number
  pipeline_metrics?: PipelineMetrics
  pipeline_metadata?: RAGMetadata
  enabled_techniques?: string[]
  tool_calls?: ToolCall[]
}

export interface ErrorEventData {
  error?: string
  message?: string
  suggestion?: string
  partial_response?: string
}

// Discriminated union for StreamEvent
export type StreamEvent =
  | {
      type: 'thinking'
      data: ThinkingEventData
      timestamp: string
    }
  | {
      type: 'tool_call'
      data: ToolCallEventData
      timestamp: string
    }
  | {
      type: 'tool_result'
      data: ToolResultEventData
      timestamp: string
    }
  | {
      type: 'response'
      data: ResponseEventData
      timestamp: string
    }
  | {
      type: 'token'
      data: TokenEventData
      timestamp: string
    }
  | {
      type: 'reasoning_token'
      data: ReasoningTokenEventData
      timestamp: string
    }
  | {
      type: 'complete'
      data: CompleteEventData
      timestamp: string
    }
  | {
      type: 'error'
      data: ErrorEventData
      timestamp: string
    }

