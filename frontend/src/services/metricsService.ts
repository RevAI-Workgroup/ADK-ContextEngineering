import { api } from './api'
import { 
  MetricsResponse, 
  MetricsComparisonResponse,
  PhaseMetricsResponse 
} from '../types/metrics.types'

export const metricsService = {
  /**
   * Get all metrics
   */
  async getAllMetrics(): Promise<MetricsResponse> {
    const response = await api.get<MetricsResponse>('/api/metrics')
    return response.data
  },

  /**
   * Get metrics for a specific phase
   */
  async getPhaseMetrics(phaseId: string): Promise<PhaseMetricsResponse> {
    const response = await api.get<PhaseMetricsResponse>(`/api/metrics/phase/${phaseId}`)
    return response.data
  },

  /**
   * Get metrics comparison across phases
   */
  async getMetricsComparison(): Promise<MetricsComparisonResponse> {
    const response = await api.get<MetricsComparisonResponse>('/api/metrics/comparison')
    return response.data
  },
}

