'use client'

/**
 * Run History Component
 * 
 * Displays the last 8 agent runs with ability to filter, select, and compare
 */

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { Badge } from '../ui/badge'
import { Checkbox } from '../ui/checkbox'
import { Separator } from '../ui/separator'
import { ScrollArea } from '../ui/scroll-area'
import {
  History,
  Trash2,
  RefreshCw,
  Search,
  GitCompare,
  Play,
  Clock,
} from 'lucide-react'
import { RunRecord, formatTimestamp } from '../../types/run.types'
import { runHistoryService } from '../../services/runHistoryService'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog'

interface RunHistoryProps {
  onCompareRuns: (runIds: string[]) => void
  onRerunWithConfig: (query: string, config: any) => void
  className?: string
}

export function RunHistory({ onCompareRuns, onRerunWithConfig, className }: RunHistoryProps) {
  const [runs, setRuns] = useState<RunRecord[]>([])
  const [filteredRuns, setFilteredRuns] = useState<RunRecord[]>([])
  const [selectedRunIds, setSelectedRunIds] = useState<Set<string>>(new Set())
  const [searchQuery, setSearchQuery] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [showClearDialog, setShowClearDialog] = useState(false)

  // Load runs on mount
  useEffect(() => {
    loadRuns()
  }, [])

  // Filter runs when search query changes
  useEffect(() => {
    if (searchQuery.trim() === '') {
      setFilteredRuns(runs)
    } else {
      const query = searchQuery.toLowerCase()
      setFilteredRuns(
        runs.filter((run) =>
          run.query.toLowerCase().includes(query) ||
          run.enabled_techniques.some((tech) => tech.toLowerCase().includes(query))
        )
      )
    }
  }, [searchQuery, runs])

  const loadRuns = async () => {
    setIsLoading(true)
    try {
      const data = await runHistoryService.getRecentRuns(8)
      setRuns(data)
      setFilteredRuns(data)
      
      // Prune selectedRunIds to only include IDs that still exist
      // Use functional update to avoid closing over stale state
      const existingIds = new Set(data.map((run) => run.id))
      setSelectedRunIds(prevSelected => {
        const prunedSelectedIds = new Set(
          Array.from(prevSelected).filter((id) => existingIds.has(id))
        )
        return prunedSelectedIds
      })
    } catch (error) {
      console.error('Failed to load runs:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleClearHistory = async () => {
    try {
      await runHistoryService.clearHistory()
      setRuns([])
      setFilteredRuns([])
      setSelectedRunIds(new Set())
      setShowClearDialog(false)
    } catch (error) {
      console.error('Failed to clear history:', error)
    }
  }

  const handleSelectRun = (runId: string, checked: boolean) => {
    const newSelected = new Set(selectedRunIds)
    if (checked) {
      newSelected.add(runId)
    } else {
      newSelected.delete(runId)
    }
    setSelectedRunIds(newSelected)
  }

  const handleCompare = () => {
    if (selectedRunIds.size >= 2) {
      onCompareRuns(Array.from(selectedRunIds))
    }
  }

  const handleRerun = (run: RunRecord) => {
    onRerunWithConfig(run.query, run.config)
  }

  return (
    <>
      <Card className={className}>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <History className="h-5 w-5" />
              <CardTitle className="text-lg">Run History</CardTitle>
              {runs.length > 0 && (
                <Badge variant="secondary" className="ml-2">
                  {runs.length}
                </Badge>
              )}
            </div>
          </div>
          <CardDescription className="mt-2">Last 8 runs with current query</CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
            {/* Search and Actions */}
            <div className="space-y-2">
              <div className="relative">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Filter by query or technique..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-8"
                />
              </div>

              <div className="flex items-center gap-2 overflow-hidden">
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={loadRuns} 
                  disabled={isLoading}
                  className="flex-shrink min-w-0"
                >
                  <RefreshCw className={`h-4 w-4 mr-2 flex-shrink-0 ${isLoading ? 'animate-spin' : ''}`} />
                  <span className="truncate">Refresh</span>
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCompare}
                  disabled={selectedRunIds.size < 2}
                  className="flex-1 min-w-0"
                >
                  <GitCompare className="h-4 w-4 mr-2 flex-shrink-0" />
                  <span className="truncate">Compare ({selectedRunIds.size})</span>
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowClearDialog(true)}
                  disabled={runs.length === 0}
                  className="flex-shrink min-w-0"
                >
                  <Trash2 className="h-4 w-4 mr-2 flex-shrink-0" />
                  <span className="truncate">Clear</span>
                </Button>
              </div>
            </div>

            <Separator />

            {/* Run List */}
            {filteredRuns.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                {runs.length === 0 ? (
                  <>
                    <History className="h-12 w-12 mx-auto mb-2 opacity-20" />
                    <p>No runs yet</p>
                    <p className="text-sm">Run queries to see history here</p>
                  </>
                ) : (
                  <>
                    <Search className="h-12 w-12 mx-auto mb-2 opacity-20" />
                    <p>No matching runs</p>
                    <p className="text-sm">Try a different search query</p>
                  </>
                )}
              </div>
            ) : (
              <ScrollArea className="h-[500px] pr-4">
                <div className="space-y-3">
                  {filteredRuns.map((run) => (
                    <RunCard
                      key={run.id}
                      run={run}
                      selected={selectedRunIds.has(run.id)}
                      onSelect={(checked) => handleSelectRun(run.id, checked)}
                      onRerun={() => handleRerun(run)}
                    />
                  ))}
                </div>
              </ScrollArea>
            )}
          </CardContent>
      </Card>

      {/* Clear Confirmation Dialog */}
      <Dialog open={showClearDialog} onOpenChange={setShowClearDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Clear Run History?</DialogTitle>
            <DialogDescription>
              This will permanently delete all {runs.length} run{runs.length !== 1 ? 's' : ''} from
              history. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowClearDialog(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleClearHistory}>
              <Trash2 className="h-4 w-4 mr-2" />
              Clear History
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

interface RunCardProps {
  run: RunRecord
  selected: boolean
  onSelect: (checked: boolean) => void
  onRerun: () => void
}

function RunCard({ run, selected, onSelect, onRerun }: RunCardProps) {
  const queryPreview = run.query.length > 80 ? run.query.substring(0, 80) + '...' : run.query

  return (
    <Card className={`transition-colors ${selected ? 'border-primary' : ''}`}>
      <CardContent className="p-4 space-y-3">
        {/* Header with checkbox and timestamp */}
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-2">
            <Checkbox
              checked={selected}
              onCheckedChange={onSelect}
              className="mt-1"
              aria-label="Select run for comparison"
            />
            <div className="flex-1">
              <p className="text-sm font-medium leading-tight">{queryPreview}</p>
            </div>
          </div>
          <Button variant="ghost" size="icon" onClick={onRerun} title="Re-run with same config" aria-label="Re-run with same config">
            <Play className="h-4 w-4" />
          </Button>
        </div>

        {/* Enabled Techniques */}
        {run.enabled_techniques.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {run.enabled_techniques.map((technique) => (
              <Badge key={technique} variant="secondary" className="text-xs">
                {technique}
              </Badge>
            ))}
          </div>
        )}

        {/* Key Metrics */}
        <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground">
          <div className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            <span>{formatTimestamp(run.timestamp)}</span>
          </div>
          <div>
            <span className="font-mono">{(run.duration_ms ?? 0).toFixed(0)}ms</span>
          </div>
          {run.metrics.latency_ms && (
            <div>
              <span>Latency: {run.metrics.latency_ms.toFixed(0)}ms</span>
            </div>
          )}
          {run.metrics.token_count && (
            <div>
              <span>Tokens: {run.metrics.token_count}</span>
            </div>
          )}
        </div>

        {/* Model */}
        <div className="flex items-center justify-between text-xs">
          <Badge variant="outline" className="text-xs">
            {run.model}
          </Badge>
        </div>
      </CardContent>
    </Card>
  )
}

