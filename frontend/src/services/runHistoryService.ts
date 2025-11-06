/**
 * Run History Service
 * 
 * Handles API calls for agent run history management and comparison
 */

import { api } from './api'
import { RunRecord, RunComparison, RunHistoryStats } from '../types/run.types'

export const runHistoryService = {
  /**
   * Get recent runs from history
   * @param limit - Maximum number of runs to return
   * @param query - Optional query text filter
   */
  async getRecentRuns(limit?: number, query?: string): Promise<RunRecord[]> {
    const params = new URLSearchParams()
    if (limit !== undefined) params.append('limit', limit.toString())
    if (query) params.append('query', query)

    const response = await api.get(`/api/runs?${params.toString()}`)
    return response.data.runs || []
  },

  /**
   * Get a specific run by ID
   */
  async getRunById(runId: string): Promise<RunRecord> {
    const response = await api.get(`/api/runs/${runId}`)
    return response.data.run
  },

  /**
   * Clear all run history
   */
  async clearHistory(): Promise<{ success: boolean; message: string }> {
    const response = await api.post('/api/runs/clear')
    return response.data
  },

  /**
   * Compare multiple runs
   * @param runIds - Array of run IDs to compare
   */
  async compareRuns(runIds: string[]): Promise<RunComparison> {
    const params = new URLSearchParams()
    runIds.forEach(id => params.append('run_ids', id))
    const response = await api.get(`/api/runs/compare?${params.toString()}`)
    return response.data
  },

  /**
   * Get run history statistics
   */
  async getHistoryStats(): Promise<RunHistoryStats> {
    const response = await api.get('/api/runs/stats')
    return response.data
  },

  /**
   * Export run history to JSON
   */
  async exportHistory(): Promise<Blob> {
    const response = await api.get('/api/runs/export', {
      responseType: 'blob',
    })
    return response.data
  },
}

