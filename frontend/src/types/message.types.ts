import { ToolCall } from './agent.types'

export type MessageRole = 'user' | 'assistant' | 'system'

export interface Message {
  id: string
  role: MessageRole
  content: string
  thinking?: string[]
  toolCalls?: ToolCall[]
  timestamp: string
  model?: string
}

// Data interfaces for each event type
export interface ThinkingEventData {
  message: string
}

export interface ToolCallEventData {
  message: string
}

export interface ResponseEventData {
  response: string
  thinking_steps?: string[]
  tool_calls?: ToolCall[]
}

export interface CompleteEventData {
  // Empty object for complete events
}

export interface ErrorEventData {
  error?: string
  message?: string
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
      type: 'response'
      data: ResponseEventData
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

