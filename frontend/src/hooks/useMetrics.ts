import { useState, useEffect, useCallback } from 'react'
import { AxiosError } from 'axios'
import { metricsService } from '../services/metricsService'
import { Metrics, MetricsComparison, PhaseData } from '../types/metrics.types'

interface LoadingState {
  metrics: boolean
  comparison: boolean
  phases: Map<string, boolean>
}

interface ErrorState {
  metrics: string | null
  comparison: string | null
  phases: Map<string, string | null>
}

export function useMetrics() {
  const [loadingState, setLoadingState] = useState<LoadingState>({
    metrics: false,
    comparison: false,
    phases: new Map<string, boolean>()
  })
  const [errorState, setErrorState] = useState<ErrorState>({
    metrics: null,
    comparison: null,
    phases: new Map<string, string | null>()
  })
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [comparison, setComparison] = useState<MetricsComparison | null>(null)

  // Helper to update specific loading flag
  const setOperationLoading = useCallback((operation: 'metrics' | 'comparison', isLoading: boolean) => {
    setLoadingState(prev => ({
      ...prev,
      [operation]: isLoading
    }))
  }, [])

  // Helper to update phase-specific loading flag
  const setPhaseLoading = useCallback((phaseId: string, isLoading: boolean) => {
    setLoadingState(prev => {
      const newPhases = new Map(prev.phases)
      if (isLoading) {
        newPhases.set(phaseId, true)
      } else {
        newPhases.delete(phaseId)
      }
      return {
        ...prev,
        phases: newPhases
      }
    })
  }, [])

  // Helper to update specific error for an operation
  const setOperationError = useCallback((operation: 'metrics' | 'comparison', error: string | null) => {
    setErrorState(prev => ({
      ...prev,
      [operation]: error
    }))
  }, [])

  // Helper to update phase-specific error
  const setPhaseError = useCallback((phaseId: string, error: string | null) => {
    setErrorState(prev => {
      const newPhases = new Map(prev.phases)
      if (error !== null) {
        newPhases.set(phaseId, error)
      } else {
        newPhases.delete(phaseId)
      }
      return {
        ...prev,
        phases: newPhases
      }
    })
  }, [])

  const fetchMetrics = useCallback(async () => {
    setOperationLoading('metrics', true)
    setOperationError('metrics', null)

    try {
      const data = await metricsService.getAllMetrics()
      setMetrics(data.metrics)
      setOperationError('metrics', null) // Clear error on success
    } catch (err: unknown) {
      if (err instanceof AxiosError) {
        setOperationError('metrics', err.response?.data?.detail || err.message || 'Failed to fetch metrics')
      } else {
        setOperationError('metrics', 'Failed to fetch metrics')
      }
    } finally {
      setOperationLoading('metrics', false)
    }
  }, [setOperationLoading, setOperationError])

  const fetchComparison = useCallback(async () => {
    setOperationLoading('comparison', true)
    setOperationError('comparison', null)

    try {
      const data = await metricsService.getMetricsComparison()
      setComparison(data.comparison)
      setOperationError('comparison', null) // Clear error on success
    } catch (err: unknown) {
      if (err instanceof AxiosError) {
        setOperationError('comparison', err.response?.data?.detail || err.message || 'Failed to fetch comparison')
      } else {
        setOperationError('comparison', 'Failed to fetch comparison')
      }
    } finally {
      setOperationLoading('comparison', false)
    }
  }, [setOperationLoading, setOperationError])

  const fetchPhaseMetrics = useCallback(async (phaseId: string): Promise<PhaseData | null> => {
    setPhaseLoading(phaseId, true)
    setPhaseError(phaseId, null)

    try {
      const data = await metricsService.getPhaseMetrics(phaseId)
      setPhaseError(phaseId, null) // Clear error on success
      return data.metrics
    } catch (err: unknown) {
      if (err instanceof AxiosError) {
        setPhaseError(phaseId, err.response?.data?.detail || err.message || 'Failed to fetch phase metrics')
      } else {
        setPhaseError(phaseId, 'Failed to fetch phase metrics')
      }
      return null
    } finally {
      setPhaseLoading(phaseId, false)
    }
  }, [setPhaseLoading, setPhaseError])

  useEffect(() => {
    fetchMetrics()
    fetchComparison()
  }, [fetchMetrics, fetchComparison])

  // Computed convenience flags for backward compatibility
  const isLoading = loadingState.metrics || loadingState.comparison || loadingState.phases.size > 0
  
  const hasError = errorState.metrics !== null || 
                   errorState.comparison !== null || 
                   Array.from(errorState.phases.values()).some(err => err !== null)

  return {
    // Granular loading state
    loading: loadingState,
    isLoading, // Convenience flag: true if any operation is loading
    
    // Granular error state
    errors: errorState,
    hasError, // Convenience flag: true if any operation has an error
    
    // Data
    metrics,
    comparison,
    
    // Actions
    fetchMetrics,
    fetchComparison,
    fetchPhaseMetrics,
  }
}

