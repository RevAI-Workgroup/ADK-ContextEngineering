import { RAGMetadata, PipelineMetrics } from './message.types'

export interface Tool {
  name: string
  description: string
  parameters: Record<string, any>
}

export interface ToolCall {
  name: string // Tool identifier
  description: string
  parameters?: Record<string, unknown> | unknown[] // Flexible input parameters
  result?: unknown // Optional tool execution result
  timestamp?: string
}

export interface AgentResponse {
  response: string
  thinking_steps?: string[]
  tool_calls?: ToolCall[]
  metrics?: ResponseMetrics
  timestamp: string
  model?: string
  pipeline_metadata?: RAGMetadata
  pipeline_metrics?: PipelineMetrics
}


export interface ResponseMetrics {
  latency_ms: number
  token_count?: number
  timestamp: string
  session_id?: string
  pipeline_metrics?: PipelineMetrics
  enabled_techniques?: string[]
}

