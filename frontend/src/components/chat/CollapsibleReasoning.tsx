import { useEffect, useRef, useState } from 'react'
import { ChevronDown, ChevronUp, Brain, Loader2 } from 'lucide-react'
import { Card, CardContent, CardHeader } from '../ui/card'
import { Button } from '../ui/button'
import { Badge } from '../ui/badge'
import { cn } from '@/lib/utils'

interface CollapsibleReasoningProps {
  reasoning: string
  isStreaming?: boolean
}

export function CollapsibleReasoning({ 
  reasoning, 
  isStreaming = false 
}: CollapsibleReasoningProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const wasStreamingRef = useRef(isStreaming)

  useEffect(() => {
    if (isStreaming) {
      setIsExpanded(true)
    } else if (wasStreamingRef.current) {
      setIsExpanded(false)
    }

    wasStreamingRef.current = isStreaming
  }, [isStreaming])
  
  if (!reasoning && !isStreaming) return null
  
  const wordCount = reasoning ? reasoning.split(/\s+/).filter(w => w.length > 0).length : 0
  
  return (
    <Card className="bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-950/20 dark:to-blue-950/20 border-purple-200 dark:border-purple-800">
      <CardHeader 
        className="cursor-pointer py-3 px-4 hover:bg-purple-100/50 dark:hover:bg-purple-900/20 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {isStreaming ? (
              <Loader2 className="h-4 w-4 text-purple-600 dark:text-purple-400 animate-spin" />
            ) : (
              <Brain className="h-4 w-4 text-purple-600 dark:text-purple-400" />
            )}
            <span className="text-sm font-semibold text-purple-900 dark:text-purple-100">
              Agent Reasoning
              {isStreaming && '...'}
            </span>
            {reasoning && (
              <Badge variant="secondary" className="ml-2 text-xs bg-white/60 dark:bg-gray-800/60">
                {wordCount} {wordCount === 1 ? 'word' : 'words'}
              </Badge>
            )}
          </div>
          <Button 
            variant="ghost" 
            size="sm" 
            className="h-6 w-6 p-0 hover:bg-purple-200/50 dark:hover:bg-purple-800/50"
            onClick={(e) => {
              e.stopPropagation()
              setIsExpanded(!isExpanded)
            }}
            aria-label={isExpanded ? "Collapse reasoning" : "Expand reasoning"}
          >
            {isExpanded ? (
              <ChevronUp className="h-4 w-4 text-purple-600 dark:text-purple-400" />
            ) : (
              <ChevronDown className="h-4 w-4 text-purple-600 dark:text-purple-400" />
            )}
          </Button>
        </div>
      </CardHeader>
      {isExpanded && (
        <CardContent className="pt-0 pb-3 px-4">
          <div className={cn(
            "text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap font-mono",
            "bg-white/50 dark:bg-gray-900/50 rounded p-3 max-h-96 overflow-y-auto",
            "border border-purple-100 dark:border-purple-900"
          )}>
            {reasoning || 'Reasoning...'}
            {isStreaming && (
              <span className="inline-block w-2 h-4 bg-purple-600 dark:bg-purple-400 ml-1 animate-pulse">
                ▊
              </span>
            )}
          </div>
        </CardContent>
      )}
    </Card>
  )
}

