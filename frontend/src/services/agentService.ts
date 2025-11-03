import { api } from './api'
import { AgentResponse, Tool } from '../types/agent.types'

export const agentService = {
  /**
   * Send a message to the agent (HTTP POST)
   */
  async sendMessage(
    message: string,
    sessionId?: string,
    includeThinking: boolean = true,
    model?: string | null,
    signal?: AbortSignal
  ): Promise<AgentResponse> {
    const response = await api.post<AgentResponse>(
      '/api/chat',
      {
        message,
        session_id: sessionId,
        include_thinking: includeThinking,
        model: model || undefined,
      },
      {
        signal,
      }
    )
    return response.data
  },

  /**
   * Get list of available tools
   */
  async getTools(): Promise<Tool[]> {
    const response = await api.get<Tool[]>('/api/tools')
    return response.data
  },

  /**
   * Get information about a specific tool
   */
  async getToolInfo(toolName: string): Promise<Tool> {
    const response = await api.get<Tool>(`/api/tools/${toolName}`)
    return response.data
  },
}

