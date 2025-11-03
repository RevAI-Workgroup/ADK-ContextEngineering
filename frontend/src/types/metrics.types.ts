export interface AggregateMetrics {
  rougeL_f1_mean?: number
  rougeL_f1_min?: number
  rougeL_f1_max?: number
  rouge1_f1_mean?: number
  rouge1_f1_min?: number
  rouge1_f1_max?: number
  rouge2_f1_mean?: number
  rouge2_f1_min?: number
  rouge2_f1_max?: number
  hallucination_rate_mean?: number
  hallucination_rate_min?: number
  hallucination_rate_max?: number
  relevance_score_mean?: number
  relevance_score_min?: number
  relevance_score_max?: number
  latency_ms_mean?: number
  tokens_per_query_mean?: number
}

export interface MetricValue {
  value: number
  metadata: Record<string, any>
}

export interface IndividualResult {
  query: string
  response: string
  ground_truth: string | null
  metrics: Record<string, MetricValue>
  latency_ms: number
  token_count: number
  timestamp: string
}

export interface PhaseData {
  phase?: string
  description?: string
  dataset?: string
  total_test_cases?: number
  successful_evaluations?: number
  failed_evaluations?: number
  success_rate?: number
  timeout_seconds?: number
  timestamp?: string
  aggregate_metrics?: AggregateMetrics
  individual_results?: IndividualResult[]
  failures?: any[]
}

export interface CurrentMetrics {
  summary: AggregateMetrics
  count: number
}

export interface Metrics {
  phase0?: PhaseData
  phase1?: PhaseData
  phase2?: PhaseData
  current?: CurrentMetrics
  [key: string]: PhaseData | CurrentMetrics | undefined
}

export interface PhaseMetrics {
  id: string
  name: string
  metrics: {
    latency_ms_mean?: number
    tokens_per_query_mean?: number
    rouge1_f1_mean?: number
    rouge2_f1_mean?: number
    rougeL_f1_mean?: number
    relevance_score_mean?: number
    hallucination_rate_mean?: number
  }
}

export interface MetricsComparison {
  phases: PhaseMetrics[]
  improvements?: Record<string, {
    baseline: number
    latest: number
    improvement_pct: number
  }>
}

export interface MetricsResponse {
  metrics: Metrics
  timestamp: string
}

export interface MetricsComparisonResponse {
  comparison: MetricsComparison
  timestamp: string
}

export interface PhaseMetricsResponse {
  phase: string
  metrics: PhaseData
  timestamp: string
}

