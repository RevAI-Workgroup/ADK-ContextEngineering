import { useMetrics } from '../hooks/useMetrics'
import { MetricsGrid } from '../components/metrics/MetricsGrid'
import { MetricsChart } from '../components/metrics/MetricsChart'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { LoadingSpinner } from '../components/common/LoadingSpinner'
import { ErrorMessage } from '../components/common/ErrorMessage'
import { Button } from '../components/ui/button'
import { RefreshCw, TrendingUp } from 'lucide-react'

export function Metrics() {
  const { loading, isLoading, errors, metrics, comparison, fetchMetrics, fetchComparison } = useMetrics()

  const handleRefresh = async () => {
    await fetchMetrics()
    await fetchComparison()
  }

  // Show loading spinner on initial load (when any data is loading and no metrics exist yet)
  if (isLoading && !metrics) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  // Show error if metrics fetch failed and we have no data
  if (errors.metrics && !metrics) {
    return <ErrorMessage message={errors.metrics} />
  }

  // Compute if refresh is in progress (either metrics or comparison loading)
  const isRefreshing = loading.metrics || loading.comparison

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="h-8 w-8 text-primary" />
            <h1 className="text-3xl font-bold">Performance Metrics</h1>
          </div>
          <p className="text-muted-foreground">
            Track context engineering improvements across phases
          </p>
        </div>
        <Button onClick={handleRefresh} disabled={isRefreshing} variant="outline" size="sm">
          <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Current Metrics */}
      {metrics?.current && (
        <div>
          <h2 className="text-xl font-semibold mb-4">Current Metrics</h2>
          <MetricsGrid
            metrics={metrics.current.summary || {}}
            comparison={comparison?.improvements}
          />
        </div>
      )}

      {/* Phase Comparison */}
      {comparison && comparison.phases && comparison.phases.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">Phase Comparison</h2>

          <div className="grid gap-4 md:grid-cols-2">
            <MetricsChart
              phases={comparison.phases}
              metric="latency_ms_mean"
              title="Latency Trend"
              description="Average response time across phases"
              type="line"
            />

            <MetricsChart
              phases={comparison.phases}
              metric="rouge1_f1_mean"
              title="Accuracy Trend"
              description="ROUGE-1 F1 score across phases"
              type="bar"
            />

            <MetricsChart
              phases={comparison.phases}
              metric="relevance_score_mean"
              title="Relevance Trend"
              description="Query-response relevance across phases"
              type="line"
            />

            <MetricsChart
              phases={comparison.phases}
              metric="hallucination_rate_mean"
              title="Hallucination Rate"
              description="Detected hallucinations across phases"
              type="bar"
            />
          </div>
        </div>
      )}

      {/* Improvements Summary */}
      {comparison?.improvements && (
        <Card>
          <CardHeader>
            <CardTitle>Key Improvements</CardTitle>
            <CardDescription>Changes from baseline (Phase 0)</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {Object.entries(comparison.improvements).map(([metric, data]) => (
                <ImprovementItem
                  key={metric}
                  metric={metric}
                  baseline={data.baseline}
                  latest={data.latest}
                  improvement={data.improvement_pct}
                />
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Phase 0 Baseline */}
      {metrics?.phase0 && (
        <Card>
          <CardHeader>
            <CardTitle>Phase 0 Baseline</CardTitle>
            <CardDescription>Initial metrics before context engineering</CardDescription>
          </CardHeader>
          <CardContent>
            <MetricsGrid metrics={metrics.phase0.aggregate_metrics || {}} />
          </CardContent>
        </Card>
      )}
    </div>
  )
}

interface ImprovementItemProps {
  metric: string
  baseline: number
  latest: number
  improvement: number
}

function ImprovementItem({ metric, baseline, latest, improvement }: ImprovementItemProps) {
  // Metrics where lower values are better
  const lowerIsBetter = ['latency_ms_mean', 'hallucination_rate_mean']
  
  // Compute effective improvement (invert for lower-is-better metrics)
  const effectiveImprovement = lowerIsBetter.includes(metric) ? -improvement : improvement
  const isPositive = effectiveImprovement > 0
  
  const metricNames: Record<string, string> = {
    latency_ms_mean: 'Latency',
    tokens_per_query_mean: 'Tokens/Query',
    rouge1_f1_mean: 'ROUGE-1 F1',
    relevance_score_mean: 'Relevance',
    hallucination_rate_mean: 'Hallucination',
  }

  return (
    <div className="p-3 rounded-lg bg-muted">
      <div className="text-sm font-medium mb-1">{metricNames[metric] || metric}</div>
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground">{baseline.toFixed(2)} →</span>
        <span className="text-sm font-medium">{latest.toFixed(2)}</span>
        <Badge variant={isPositive ? 'default' : 'destructive'} className="ml-auto">
          {isPositive ? '↑' : '↓'} {Math.abs(effectiveImprovement).toFixed(1)}%
        </Badge>
      </div>
    </div>
  )
}

