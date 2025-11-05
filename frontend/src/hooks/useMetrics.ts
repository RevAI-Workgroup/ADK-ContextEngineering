import { useState, useEffect, useCallback, useRef } from 'react'
import { AxiosError } from 'axios'
import { metricsService } from '../services/metricsService'
import { runHistoryService } from '../services/runHistoryService'
import { Metrics, MetricsComparison, PhaseData } from '../types/metrics.types'
import { RunRecord, RunComparison } from '../types/run.types'

interface LoadingState {
  metrics: boolean
  comparison: boolean
  phases: Map<string, boolean>
  runs: boolean
  runComparison: boolean
}

interface ErrorState {
  metrics: string | null
  comparison: string | null
  phases: Map<string, string | null>
  runs: string | null
  runComparison: string | null
}

export function useMetrics() {
  const [loadingState, setLoadingState] = useState<LoadingState>({
    metrics: false,
    comparison: false,
    phases: new Map<string, boolean>(),
    runs: false,
    runComparison: false
  })
  const [errorState, setErrorState] = useState<ErrorState>({
    metrics: null,
    comparison: null,
    phases: new Map<string, string | null>(),
    runs: null,
    runComparison: null
  })
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [comparison, setComparison] = useState<MetricsComparison | null>(null)
  const [runs, setRuns] = useState<RunRecord[]>([])
  const [selectedRunIds, setSelectedRunIds] = useState<string[]>([])
  const [runComparison, setRunComparison] = useState<RunComparison | null>(null)
  const latestRunComparisonKey = useRef<string | null>(null)

  // Helper to update specific loading flag
  const setOperationLoading = useCallback((operation: 'metrics' | 'comparison' | 'runs' | 'runComparison', isLoading: boolean) => {
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
  const setOperationError = useCallback((operation: 'metrics' | 'comparison' | 'runs' | 'runComparison', error: string | null) => {
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

  const fetchRuns = useCallback(async (limit?: number, query?: string) => {
    setOperationLoading('runs', true)
    setOperationError('runs', null)

    try {
      const data = await runHistoryService.getRecentRuns(limit, query)
      setRuns(data)
      setOperationError('runs', null)
    } catch (err: unknown) {
      if (err instanceof AxiosError) {
        setOperationError('runs', err.response?.data?.detail || err.message || 'Failed to fetch runs')
      } else {
        setOperationError('runs', 'Failed to fetch runs')
      }
    } finally {
      setOperationLoading('runs', false)
    }
  }, [setOperationLoading, setOperationError])

  const fetchRunComparison = useCallback(async (runIds: string[]) => {
    if (runIds.length === 0) {
      latestRunComparisonKey.current = null
      setOperationLoading('runComparison', false)
      setOperationError('runComparison', null)
      setRunComparison(null)
      return
    }

    setOperationLoading('runComparison', true)
    setOperationError('runComparison', null)
    const requestKey = JSON.stringify([...runIds].sort())
    latestRunComparisonKey.current = requestKey

    try {
      const data = await runHistoryService.compareRuns(runIds)
      if (latestRunComparisonKey.current !== requestKey) {
        return
      }
      setRunComparison(data)
      setOperationError('runComparison', null)
    } catch (err: unknown) {
      if (err instanceof AxiosError) {
        setOperationError('runComparison', err.response?.data?.detail || err.message || 'Failed to compare runs')
      } else {
        setOperationError('runComparison', 'Failed to compare runs')
      }
    } finally {
      if (latestRunComparisonKey.current === requestKey) {
        setOperationLoading('runComparison', false)
      }
    }
  }, [setOperationLoading, setOperationError])

  useEffect(() => {
    fetchMetrics()
    fetchComparison()
    fetchRuns()
  }, [fetchMetrics, fetchComparison, fetchRuns])

  // Update run comparison when selected runs change
  useEffect(() => {
    if (selectedRunIds.length > 0) {
      fetchRunComparison(selectedRunIds)
    } else {
      latestRunComparisonKey.current = null
      setOperationLoading('runComparison', false)
      setOperationError('runComparison', null)
      setRunComparison(null)
    }
  }, [selectedRunIds, fetchRunComparison])

  // Computed convenience flags for backward compatibility
  const isLoading = loadingState.metrics || loadingState.comparison || loadingState.phases.size > 0 || 
                    loadingState.runs || loadingState.runComparison
  
  const hasError = errorState.metrics !== null || 
                   errorState.comparison !== null || 
                   errorState.runs !== null ||
                   errorState.runComparison !== null ||
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
    runs,
    selectedRunIds,
    runComparison,
    
    // Actions
    fetchMetrics,
    fetchComparison,
    fetchPhaseMetrics,
    fetchRuns,
    fetchRunComparison,
    setSelectedRunIds,
  }
}

