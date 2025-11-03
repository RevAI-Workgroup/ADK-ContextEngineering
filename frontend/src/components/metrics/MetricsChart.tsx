import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { PhaseMetrics } from '../../types/metrics.types'

interface MetricsChartProps {
  phases: PhaseMetrics[]
  metric: keyof PhaseMetrics['metrics']
  title: string
  description?: string
  type?: 'line' | 'bar'
}

export function MetricsChart({
  phases,
  metric,
  title,
  description,
  type = 'line',
}: MetricsChartProps) {
  // Transform data for recharts
  const data = phases.map((phase) => ({
    name: phase.id,
    value: phase.metrics[metric as keyof typeof phase.metrics] || 0,
  }))

  const Chart = type === 'line' ? LineChart : BarChart

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <Chart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            {type === 'line' ? (
              <Line type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} />
            ) : (
              <Bar dataKey="value" fill="#3b82f6" />
            )}
          </Chart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}

