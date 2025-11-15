import { useState, useMemo } from 'react'
import { useMetrics } from '../hooks/useMetrics'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { LoadingSpinner } from '../components/common/LoadingSpinner'
import { ErrorMessage } from '../components/common/ErrorMessage'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Checkbox } from '../components/ui/checkbox'
import { RefreshCw, TrendingUp, BarChart3, Filter } from 'lucide-react'
import { isMetricBetterWhenHigher, formatTimestamp, RunComparison, RunRecord } from '../types/run.types'
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts'

export function Metrics() {
  const { 
    loading, 
    isLoading, 
    errors, 
    runs, 
    selectedRunIds, 
    setSelectedRunIds,
    runComparison,
    fetchRuns 
  } = useMetrics()

  // Filter state
  const [queryFilter, setQueryFilter] = useState('')
  const [techniqueFilter, setTechniqueFilter] = useState<string[]>([])
  const [dateRange, setDateRange] = useState({ start: '', end: '' })

  // Get all unique techniques from runs
  const allTechniques = useMemo(() => {
    const techniques = new Set<string>()
    runs.forEach(run => {
      run.enabled_techniques.forEach(tech => techniques.add(tech))
    })
    return Array.from(techniques).sort()
  }, [runs])

  // Filter runs based on criteria
  const filteredRuns = useMemo(() => {
    return runs.filter(run => {
      // Query filter
      if (queryFilter && !run.query.toLowerCase().includes(queryFilter.toLowerCase())) {
        return false
      }

      // Technique filter
      if (techniqueFilter.length > 0) {
        const hasAllTechniques = techniqueFilter.every(tech => 
          run.enabled_techniques.includes(tech)
        )
        if (!hasAllTechniques) return false
      }

      // Date range filter
      if (dateRange.start) {
        const runDate = new Date(run.timestamp)
        const startDate = new Date(dateRange.start)
        if (runDate < startDate) return false
      }
      if (dateRange.end) {
        const runDate = new Date(run.timestamp)
        const endDate = new Date(dateRange.end)
        endDate.setHours(23, 59, 59, 999) // Include the entire end date
        if (runDate > endDate) return false
      }

      return true
    })
  }, [runs, queryFilter, techniqueFilter, dateRange])

  const handleRefresh = async () => {
    await fetchRuns()
  }

  const handleRunSelection = (runId: string, checked: boolean) => {
    if (checked) {
      setSelectedRunIds(prev => [...prev, runId])
    } else {
      setSelectedRunIds(prev => prev.filter(id => id !== runId))
    }
  }

  const handleSelectAll = () => {
    setSelectedRunIds(filteredRuns.map(run => run.id))
  }

  const handleClearSelection = () => {
    setSelectedRunIds([])
  }

  // Show loading spinner on initial load
  if (isLoading && runs.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  // Show error if runs fetch failed and we have no data
  if (errors.runs && runs.length === 0) {
    return <ErrorMessage message={errors.runs} />
  }

  const isRefreshing = loading.runs || loading.runComparison

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="h-8 w-8 text-primary" />
            <h1 className="text-3xl font-bold">Run Comparison</h1>
          </div>
          <p className="text-muted-foreground">
            Compare context engineering techniques across different runs
          </p>
        </div>
        <Button onClick={handleRefresh} disabled={isRefreshing} variant="outline" size="sm">
          <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Filter className="h-5 w-5" />
            <CardTitle>Filters</CardTitle>
          </div>
          <CardDescription>Filter runs by query, techniques, or date range</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="query-filter">Query Text</Label>
              <Input
                id="query-filter"
                placeholder="Search queries..."
                value={queryFilter}
                onChange={(e) => setQueryFilter(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="date-start">Start Date</Label>
              <Input
                id="date-start"
                type="date"
                value={dateRange.start}
                onChange={(e) => setDateRange({ ...dateRange, start: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="date-end">End Date</Label>
              <Input
                id="date-end"
                type="date"
                value={dateRange.end}
                onChange={(e) => setDateRange({ ...dateRange, end: e.target.value })}
              />
            </div>
          </div>

          {allTechniques.length > 0 && (
            <div className="space-y-2">
              <Label>Enabled Techniques</Label>
              <div className="flex flex-wrap gap-3">
                {allTechniques.map(tech => (
                  <div key={tech} className="flex items-center space-x-2">
                    <Checkbox
                      id={`tech-${tech}`}
                      checked={techniqueFilter.includes(tech)}
                      onCheckedChange={(checked) => {
                        if (checked) {
                          setTechniqueFilter([...techniqueFilter, tech])
                        } else {
                          setTechniqueFilter(techniqueFilter.filter(t => t !== tech))
                        }
                      }}
                    />
                    <label
                      htmlFor={`tech-${tech}`}
                      className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                    >
                      {tech}
                    </label>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Run Selector */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Select Runs to Compare</CardTitle>
              <CardDescription>
                {filteredRuns.length} run(s) available • {selectedRunIds.length} selected
              </CardDescription>
            </div>
            <div className="flex gap-2">
              <Button onClick={handleSelectAll} variant="outline" size="sm">
                Select All
              </Button>
              <Button onClick={handleClearSelection} variant="outline" size="sm">
                Clear
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 max-h-[400px] overflow-y-auto">
            {filteredRuns.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">
                No runs found matching the current filters
              </p>
            ) : (
              filteredRuns.map(run => (
                <div
                  key={run.id}
                  className="flex items-start gap-3 p-3 rounded-lg border hover:bg-muted/50 transition-colors"
                >
                  <Checkbox
                    checked={selectedRunIds.includes(run.id)}
                    onCheckedChange={(checked) => handleRunSelection(run.id, checked as boolean)}
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{run.query}</p>
                    <div className="flex items-center gap-2 mt-1 flex-wrap">
                      <span className="text-xs text-muted-foreground">
                        {formatTimestamp(run.timestamp)}
                      </span>
                      <span className="text-xs text-muted-foreground">•</span>
                      <span className="text-xs text-muted-foreground">{run.model}</span>
                      {run.enabled_techniques.length > 0 && (
                        <>
                          <span className="text-xs text-muted-foreground">•</span>
                          <div className="flex gap-1">
                            {run.enabled_techniques.map(tech => (
                              <Badge key={tech} variant="secondary" className="text-xs">
                                {tech}
                              </Badge>
                            ))}
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      {/* Charts */}
      {runComparison && selectedRunIds.length > 0 && (
        <RunComparisonCharts runComparison={runComparison} />
      )}

      {/* No selection message */}
      {selectedRunIds.length === 0 && filteredRuns.length > 0 && (
        <Card>
          <CardContent className="py-12 text-center">
            <BarChart3 className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">No Runs Selected</h3>
            <p className="text-sm text-muted-foreground">
              Select runs from the list above to visualize and compare their metrics
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

interface RunComparisonChartsProps {
  runComparison: RunComparison | null
}

function RunComparisonCharts({ runComparison }: RunComparisonChartsProps) {
  if (!runComparison || !runComparison.runs || runComparison.runs.length === 0) {
    return null
  }

  // Prepare data for charts
  const chartData = runComparison.runs.map((run: RunRecord, index: number) => ({
    name: `Run ${index + 1}`,
    runId: run.id,
    timestamp: formatTimestamp(run.timestamp),
    metrics: run.metrics
  }))

  // Get common metrics
  const metricKeys = useMemo(() => {
    return runComparison.metrics_comparison 
      ? Object.keys(runComparison.metrics_comparison)
      : []
  }, [runComparison.metrics_comparison])

  // Technique impact data - calculate deltas from first run (baseline)
  interface TechniqueImpactItem {
    metric: string
    deltas: number[]
    values: number[]
  }

  interface TechniqueImpactChartData {
    metric: string
    run: string
    delta: number
    isPositive: boolean
  }

  const techniqueImpactData = useMemo(() => {
    return metricKeys.map(metricKey => {
      const metricComparison = runComparison.metrics_comparison[metricKey]
      if (!metricComparison || !metricComparison.values || metricComparison.values.length < 2) {
        return null
      }

      const baseline = metricComparison.values[0]

      // Skip metrics where baseline is zero to avoid Infinity/NaN in percentage calculations
      if (Math.abs(baseline) < 1e-9) {
        return null
      }

      const deltas = metricComparison.values.map((value: number, index: number) => {
        if (index === 0) return 0
        const percentChange = ((value - baseline) / baseline) * 100
        return percentChange
      })

      return {
        metric: metricKey,
        deltas,
        values: metricComparison.values
      }
    }).filter((item): item is TechniqueImpactItem => item !== null)
  }, [metricKeys, runComparison.metrics_comparison])

  // Compute chart data for Technique Impact chart with conditional coloring
  const techniqueImpactChartData = useMemo(() => {
    return techniqueImpactData.flatMap((item: TechniqueImpactItem): TechniqueImpactChartData[] => 
      item.deltas.map((delta: number, index: number): TechniqueImpactChartData => ({
        metric: item.metric,
        run: `Run ${index + 1}`,
        delta: delta,
        isPositive: isMetricBetterWhenHigher(item.metric) ? delta > 0 : delta < 0
      }))
    ).filter((item: TechniqueImpactChartData) => item.run !== 'Run 1')
  }, [techniqueImpactData])

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Run Comparison Charts</h2>

      <div className="grid gap-4 md:grid-cols-2">
        {/* Latency Comparison */}
        {chartData[0]?.metrics?.latency_ms !== undefined && (
          <Card>
            <CardHeader>
              <CardTitle>Latency Comparison</CardTitle>
              <CardDescription>Response time across selected runs</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis label={{ value: 'ms', angle: -90, position: 'insideLeft' }} />
                  <Tooltip />
                  <Bar dataKey="metrics.latency_ms" fill="hsl(var(--primary))" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )}

        {/* Token Count Comparison */}
        {chartData[0]?.metrics?.token_count !== undefined && (
          <Card>
            <CardHeader>
              <CardTitle>Token Usage</CardTitle>
              <CardDescription>Token consumption across runs</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="metrics.token_count" fill="hsl(var(--chart-2))" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )}

        {/* Relevance Score Comparison */}
        {chartData[0]?.metrics?.relevance_score !== undefined && (
          <Card>
            <CardHeader>
              <CardTitle>Relevance Score</CardTitle>
              <CardDescription>Query-response relevance</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis domain={[0, 1]} />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="metrics.relevance_score" stroke="hsl(var(--chart-3))" />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )}

        {/* Accuracy Comparison */}
        {chartData[0]?.metrics?.accuracy !== undefined && (
          <Card>
            <CardHeader>
              <CardTitle>Accuracy</CardTitle>
              <CardDescription>Answer accuracy across runs</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis domain={[0, 1]} />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="metrics.accuracy" stroke="hsl(var(--chart-4))" />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Technique Impact Chart */}
      {techniqueImpactData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Technique Impact</CardTitle>
            <CardDescription>
              Percentage change from baseline (Run 1) across all metrics
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={400}>
              <BarChart
                data={techniqueImpactChartData}
                layout="vertical"
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" label={{ value: '% Change', position: 'insideBottom', offset: -5 }} />
                <YAxis type="category" dataKey="metric" width={150} />
                <Tooltip />
                <Legend />
                <Bar dataKey="delta">
                  {techniqueImpactChartData.map((entry: TechniqueImpactChartData, index: number) => (
                    <Cell key={`cell-${index}`} fill={entry.isPositive ? '#22c55e' : '#ef4444'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Metrics Summary Table */}
      <Card>
        <CardHeader>
          <CardTitle>Metrics Summary</CardTitle>
          <CardDescription>Side-by-side comparison of all metrics</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2 px-2">Metric</th>
                  {runComparison.runs.map((run: RunRecord, index: number) => (
                    <th key={run.id} className="text-right py-2 px-2">
                      Run {index + 1}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {metricKeys.map(metricKey => {
                  const metricComparison = runComparison.metrics_comparison[metricKey]
                  if (!metricComparison) return null

                  return (
                    <tr key={metricKey} className="border-b">
                      <td className="py-2 px-2 font-medium">{metricKey}</td>
                      {metricComparison.values.map((value: number, index: number) => {
                        const isBest = index === metricComparison.best_index
                        const isWorst = index === metricComparison.worst_index
                        return (
                          <td key={index} className="text-right py-2 px-2">
                            <span className={
                              isBest ? 'text-green-600 font-semibold' : 
                              isWorst ? 'text-red-600' : ''
                            }>
                              {value?.toFixed(2) ?? 'N/A'}
                            </span>
                          </td>
                        )
                      })}
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

