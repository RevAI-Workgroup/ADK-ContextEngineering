import { MetricsCard } from './MetricsCard'
import { Clock, Zap, FileText, DollarSign, Target, AlertTriangle } from 'lucide-react'

interface MetricsGridProps {
  metrics: {
    latency_ms_mean?: number
    tokens_per_query_mean?: number
    rouge1_f1_mean?: number
    relevance_score_mean?: number
    hallucination_rate_mean?: number
    cost_per_query?: number
  }
  comparison?: Record<string, {
    baseline: number
    latest: number
    improvement_pct: number
  }>
}

export function MetricsGrid({ metrics, comparison }: MetricsGridProps) {
  const getTrend = (metricName: string) => {
    if (!comparison || !comparison[metricName]) return undefined

    const { improvement_pct } = comparison[metricName]
    // For some metrics, lower is better (latency, hallucination, cost)
    const lowerIsBetter = ['latency_ms_mean', 'hallucination_rate_mean', 'cost_per_query'].includes(metricName)

    return {
      // Value must be non-negative (magnitude of change)
      value: Math.abs(improvement_pct),
      // isPositive indicates the direction (true = improvement, false = decline)
      isPositive: lowerIsBetter ? improvement_pct < 0 : improvement_pct > 0,
    }
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      <MetricsCard
        title="Avg Latency"
        value={metrics.latency_ms_mean || 0}
        unit="ms"
        description="Average response time"
        icon={Clock}
        trend={getTrend('latency_ms_mean')}
      />

      <MetricsCard
        title="Tokens per Query"
        value={metrics.tokens_per_query_mean || 0}
        unit="tokens"
        description="Average token usage"
        icon={FileText}
        trend={getTrend('tokens_per_query_mean')}
      />

      <MetricsCard
        title="ROUGE-1 F1"
        value={metrics.rouge1_f1_mean || 0}
        description="Answer accuracy score"
        icon={Target}
        trend={getTrend('rouge1_f1_mean')}
      />

      <MetricsCard
        title="Relevance Score"
        value={metrics.relevance_score_mean || 0}
        description="Query-response relevance"
        icon={Zap}
        trend={getTrend('relevance_score_mean')}
      />

      <MetricsCard
        title="Hallucination Rate"
        value={metrics.hallucination_rate_mean || 0}
        description="Detected hallucinations"
        icon={AlertTriangle}
        trend={getTrend('hallucination_rate_mean')}
      />

      {metrics.cost_per_query !== undefined && (
        <MetricsCard
          title="Cost per Query"
          value={metrics.cost_per_query}
          unit="USD"
          description="Estimated cost"
          icon={DollarSign}
          trend={getTrend('cost_per_query')}
        />
      )}
    </div>
  )
}

