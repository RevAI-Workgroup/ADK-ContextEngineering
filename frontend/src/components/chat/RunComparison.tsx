/**
 * Run Comparison Component
 * 
 * Displays side-by-side comparison of multiple agent runs
 * Shows configuration differences, response variations, and metric deltas
 */

import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../ui/dialog'
import { Button } from '../ui/button'
import { Badge } from '../ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { Separator } from '../ui/separator'
import { ScrollArea } from '../ui/scroll-area'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs'
import {
  Download,
  TrendingUp,
  TrendingDown,
  Minus,
  AlertCircle,
  CheckCircle,
  XCircle,
} from 'lucide-react'
import { RunComparison as RunComparisonType, isMetricBetterWhenHigher } from '../../types/run.types'
import { runHistoryService } from '../../services/runHistoryService'
import { TECHNIQUE_NAMES } from '../../types/config.types'

interface RunComparisonProps {
  runIds: string[]
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function RunComparison({ runIds, open, onOpenChange }: RunComparisonProps) {
  const [comparison, setComparison] = useState<RunComparisonType | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (open && runIds.length >= 2) {
      loadComparison()
    }
  }, [open, runIds])

  const loadComparison = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await runHistoryService.compareRuns(runIds)
      setComparison(data)
    } catch (err: any) {
      console.error('Failed to load comparison:', err)
      setError(err.response?.data?.detail || 'Failed to compare runs')
    } finally {
      setIsLoading(false)
    }
  }

  const handleExport = () => {
    if (!comparison) return

    const dataStr = JSON.stringify(comparison, null, 2)
    const blob = new Blob([dataStr], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `run-comparison-${Date.now()}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-6xl max-h-[90vh]">
        <DialogHeader>
          <DialogTitle>Run Comparison</DialogTitle>
          <DialogDescription>
            Comparing {runIds.length} runs side-by-side
          </DialogDescription>
        </DialogHeader>

        {isLoading && (
          <div className="flex items-center justify-center py-12">
            <div className="text-center space-y-2">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto" />
              <p className="text-sm text-muted-foreground">Loading comparison...</p>
            </div>
          </div>
        )}

        {error && (
          <div className="flex items-center justify-center py-12">
            <Card className="border-destructive">
              <CardContent className="pt-6">
                <div className="flex items-center gap-2 text-destructive">
                  <AlertCircle className="h-5 w-5" />
                  <p>{error}</p>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {!isLoading && !error && comparison && (
          <ScrollArea className="h-[600px] pr-4">
            <div className="space-y-6">
              {/* Query Display */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Query</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm">{comparison.query}</p>
                </CardContent>
              </Card>

              {/* Tabs for different views */}
              <Tabs defaultValue="metrics" className="w-full">
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="metrics">Metrics</TabsTrigger>
                  <TabsTrigger value="config">Configuration</TabsTrigger>
                  <TabsTrigger value="responses">Responses</TabsTrigger>
                </TabsList>

                {/* Metrics Comparison */}
                <TabsContent value="metrics" className="space-y-4">
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">Metrics Comparison</CardTitle>
                      <CardDescription>
                        Color-coded: <Badge variant="default" className="bg-green-500 text-xs mx-1">Best</Badge>
                        <Badge variant="destructive" className="text-xs mx-1">Worst</Badge>
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        {Object.entries(comparison.metrics_comparison).map(([metric, data]) => (
                          <MetricRow
                            key={metric}
                            metricName={metric}
                            values={data.values}
                            bestIndex={data.best_index}
                            worstIndex={data.worst_index}
                            runCount={comparison.runs.length}
                          />
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>

                {/* Configuration Comparison */}
                <TabsContent value="config" className="space-y-4">
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">Enabled Techniques</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-1 gap-3">
                        {comparison.runs.map((run, idx) => (
                          <div key={run.id} className="space-y-2">
                            <div className="flex items-center gap-2">
                              <Badge variant="outline">Run {idx + 1}</Badge>
                              <span className="text-xs text-muted-foreground">{run.model}</span>
                            </div>
                            <div className="flex flex-wrap gap-1">
                              {run.enabled_techniques.length > 0 ? (
                                run.enabled_techniques.map((tech) => (
                                  <Badge key={tech} variant="secondary" className="text-xs">
                                    {TECHNIQUE_NAMES[tech] || tech}
                                  </Badge>
                                ))
                              ) : (
                                <Badge variant="outline" className="text-xs">
                                  Baseline (No techniques)
                                </Badge>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>

                  {comparison.config_comparison.differences.length > 0 && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base">Configuration Differences</CardTitle>
                        <CardDescription>Parameters that differ between runs</CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-3">
                          {comparison.config_comparison.differences.map((diff, idx) => (
                            <div key={idx} className="space-y-1">
                              <div className="font-medium text-sm">
                                {TECHNIQUE_NAMES[diff.technique] || diff.technique} - {diff.parameter}
                              </div>
                              <div className="grid grid-cols-1 gap-1">
                                {diff.values.map((value, runIdx) => (
                                  <div key={runIdx} className="flex items-center gap-2 text-sm">
                                    <Badge variant="outline" className="text-xs">Run {runIdx + 1}</Badge>
                                    <span className="font-mono">{JSON.stringify(value)}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </TabsContent>

                {/* Responses Comparison */}
                <TabsContent value="responses" className="space-y-4">
                  {comparison.runs.map((run, idx) => (
                    <Card key={run.id}>
                      <CardHeader>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <CardTitle className="text-base">Run {idx + 1}</CardTitle>
                            <Badge variant="outline" className="text-xs">{run.model}</Badge>
                          </div>
                          <div className="flex gap-1">
                            {run.enabled_techniques.map((tech) => (
                              <Badge key={tech} variant="secondary" className="text-xs">
                                {TECHNIQUE_NAMES[tech] || tech}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      </CardHeader>
                      <CardContent>
                        <ScrollArea className="h-[200px] w-full">
                          <p className="text-sm whitespace-pre-wrap">{run.response}</p>
                        </ScrollArea>
                      </CardContent>
                    </Card>
                  ))}
                </TabsContent>
              </Tabs>
            </div>
          </ScrollArea>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={handleExport} disabled={!comparison}>
            <Download className="h-4 w-4 mr-2" />
            Export JSON
          </Button>
          <Button onClick={() => onOpenChange(false)}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

interface MetricRowProps {
  metricName: string
  values: number[]
  bestIndex: number
  worstIndex: number
  runCount: number
}

function MetricRow({ metricName, values, bestIndex, worstIndex, runCount }: MetricRowProps) {
  const betterWhenHigher = isMetricBetterWhenHigher(metricName)

  const getBadgeVariant = (index: number) => {
    if (index === bestIndex) return 'default'
    if (index === worstIndex) return 'destructive'
    return 'secondary'
  }

  const getBadgeColor = (index: number) => {
    if (index === bestIndex) return 'bg-green-500'
    if (index === worstIndex) return 'bg-red-500'
    return ''
  }

  const getIcon = (index: number) => {
    if (runCount === 2) {
      if (index === bestIndex) return <CheckCircle className="h-3 w-3" />
      if (index === worstIndex) return <XCircle className="h-3 w-3" />
    }
    return null
  }

  const formatValue = (value: number): string => {
    if (metricName.includes('rate') || metricName.includes('score')) {
      return value.toFixed(3)
    }
    return value.toFixed(2)
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">{metricName}</span>
        {betterWhenHigher ? (
          <TrendingUp className="h-4 w-4 text-green-500" />
        ) : (
          <TrendingDown className="h-4 w-4 text-blue-500" />
        )}
      </div>
      <div className="grid grid-cols-1 gap-2">
        {values.map((value, idx) => (
          <div key={idx} className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">Run {idx + 1}</span>
            <Badge variant={getBadgeVariant(idx)} className={`${getBadgeColor(idx)} font-mono text-xs`}>
              {getIcon(idx)}
              <span className={getIcon(idx) ? 'ml-1' : ''}>{formatValue(value)}</span>
            </Badge>
          </div>
        ))}
      </div>
      {runCount > 1 && (
        <div className="text-xs text-muted-foreground">
          Range: {formatValue(Math.min(...values))} - {formatValue(Math.max(...values))}
        </div>
      )}
      <Separator />
    </div>
  )
}

