/**
 * Metrics utility functions for consistent improvement direction handling
 */

/**
 * List of metrics where lower values indicate better performance
 */
export const LOWER_IS_BETTER_METRICS = [
  'latency_ms_mean',
  'hallucination_rate_mean',
  'cost_per_query',
] as const

/**
 * Check if a metric follows the "lower is better" paradigm
 * 
 * @param metric - The metric name to check
 * @returns true if lower values are better, false otherwise
 */
export function isLowerBetter(metric: string): boolean {
  return LOWER_IS_BETTER_METRICS.includes(metric as any)
}

