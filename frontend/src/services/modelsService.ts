import { api } from './api'

export interface OllamaModel {
  name: string
  modified_at: string
  size: number
  digest?: string
}

export interface RunningModel {
  name: string
  size: number
  size_vram: number
}

export interface ClearModelsResponse {
  success: boolean
  models_stopped: string[]
  message: string
}

export const modelsService = {
  /**
   * Get list of locally installed Ollama models
   */
  async getModels(): Promise<OllamaModel[]> {
    const response = await api.get<OllamaModel[]>('/api/models')
    return response.data
  },

  /**
   * Get list of currently running (loaded in memory) models
   */
  async getRunningModels(): Promise<RunningModel[]> {
    const response = await api.get<RunningModel[]>('/api/models/running')
    return response.data
  },

  /**
   * Stop all currently running models to free up memory
   */
  async clearRunningModels(): Promise<ClearModelsResponse> {
    const response = await api.post<ClearModelsResponse>('/api/models/clear')
    return response.data
  },
}

