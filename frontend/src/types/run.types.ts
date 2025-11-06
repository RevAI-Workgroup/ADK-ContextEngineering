/**
 * Run history types for tracking and comparing agent runs
 * 
 * These types mirror the Python backend run history system defined in
 * src/memory/run_history.py
 */

import { ContextEngineeringConfig } from './config.types'

export interface RunRecord {
  id: string
  query: string
  config: ContextEngineeringConfig
  response: string
  metrics: Record<string, any>
  timestamp: string
  model: string
  duration_ms: number
  enabled_techniques: string[]
}

export interface RunSummary {
  id: string
  query_preview: string
  timestamp: string
  model: string
  duration_ms: number
  enabled_techniques: string[]
  key_metrics: Record<string, any>
}

export interface MetricComparison {
  metric_name?: string  // Optional when used as dictionary value (key is the metric name)
  values: number[]
  best_index: number
  worst_index: number
  differences: number[]  // Differences between runs (first run is baseline: 0)
  improvement_pct?: number  // Optional percentage improvement calculation
}

export interface ConfigDifference {
  technique: string
  parameter: string
  values: any[]
}

export interface RunComparison {
  runs: RunRecord[]
  query: string
  metrics_comparison: Record<string, Omit<MetricComparison, 'metric_name'>>
  config_comparison: {
    differences: ConfigDifference[]
    enabled_techniques: string[][]
  }
  timestamp: string
}

export interface RunHistoryStats {
  total_runs: number
  models_used: string[]
  techniques_used: string[]
  date_range: {
    earliest: string
    latest: string
  } | null
  average_duration_ms: number
}

// Helper function to format run for display
export const formatRunPreview = (run: RunRecord): RunSummary => {
  const queryPreview = run.query.length > 100 
    ? run.query.substring(0, 100) + '...' 
    : run.query

  return {
    id: run.id,
    query_preview: queryPreview,
    timestamp: run.timestamp,
    model: run.model,
    duration_ms: run.duration_ms,
    enabled_techniques: run.enabled_techniques,
    key_metrics: {
      latency_ms: run.metrics.latency_ms ?? null,
      token_count: run.metrics.token_count ?? null,
      relevance_score: run.metrics.relevance_score ?? null,
      accuracy: run.metrics.accuracy ?? null,
    },
  }
}

// Helper to format timestamp for display
export const formatTimestamp = (timestamp: string): string => {
  const date = new Date(timestamp)
  
  // Validate the parsed date immediately
  if (isNaN(date.getTime())) {
    return 'Invalid date'
  }
  
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  
  return date.toLocaleDateString()
}

// Helper to determine if metric is "better" when higher or lower
export const isMetricBetterWhenHigher = (metricName: string): boolean => {
  const lowerIsBetter = [
    'latency_ms',
    'duration_ms',
    'token_count',
    'hallucination_rate',
    'error_rate',
    'cost',
  ]
  
  return !lowerIsBetter.some(metric => metricName.toLowerCase().includes(metric))
}

