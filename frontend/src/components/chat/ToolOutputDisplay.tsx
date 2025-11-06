import { useState } from 'react'
import { Wrench, ChevronDown, ChevronRight } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'
import { Badge } from '../ui/badge'
import { ToolCall } from '../../types/agent.types'
import { cn } from '@/lib/utils'

interface ToolOutputDisplayProps {
  toolCalls: ToolCall[]
}

/**
 * Render a collapsible card that displays a list of tool call entries.
 *
 * Each entry shows the tool name, optional timestamp, optional description,
 * optional parameters (pretty-printed JSON), and an optional result (string or pretty-printed JSON).
 *
 * @param toolCalls - Array of ToolCall entries to display; each entry may include `name`, `timestamp`, `description`, `parameters`, and `result`
 * @returns A React element containing the collapsible "Tool Calls" card with a badge showing the count
 */
export function ToolOutputDisplay({ toolCalls }: ToolOutputDisplayProps) {
  // Start expanded by default to show tool information
  const [isExpanded, setIsExpanded] = useState(true)

  return (
    <Card className={cn('border border-amber-200 bg-amber-50')}>
      <CardHeader
        className="p-3 cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {isExpanded ? <ChevronDown className="h-4 w-4 text-gray-700" /> : <ChevronRight className="h-4 w-4 text-gray-700" />}
            <div className="flex items-center gap-2 text-amber-600">
              <Wrench className="h-4 w-4" />
              <CardTitle className="text-sm font-medium">
                Tool Calls
              </CardTitle>
            </div>
          </div>
          <Badge variant="secondary" className="text-xs bg-white">
            {toolCalls.length} {toolCalls.length === 1 ? 'tool' : 'tools'}
          </Badge>
        </div>
      </CardHeader>

      {isExpanded && (
        <CardContent className="p-3 pt-0 space-y-3">
          {toolCalls.map((toolCall, index) => (
            <div key={toolCall.timestamp || `tool-${index}`} className="bg-white p-3 rounded border border-amber-200">
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Wrench className="h-4 w-4 text-amber-600" />
                  <span className="text-sm font-medium text-gray-900">
                    {toolCall.name}
                  </span>
                </div>
                {toolCall.timestamp && (
                  <span className="text-xs text-gray-600">
                    {new Date(toolCall.timestamp).toLocaleTimeString()}
                  </span>
                )}
              </div>

              {toolCall.description && (
                <p className="text-sm text-gray-700 mb-2">{toolCall.description}</p>
              )}

              {toolCall.parameters && (
                <div className="mb-2">
                  <div className="text-xs font-medium mb-1 text-gray-900">Parameters:</div>
                  <div className="text-sm text-gray-800 bg-gray-50 p-2 rounded border border-gray-200 max-h-48 overflow-y-auto">
                    <pre className="whitespace-pre-wrap font-mono text-xs">
                      {JSON.stringify(toolCall.parameters, null, 2)}
                    </pre>
                  </div>
                </div>
              )}

              {toolCall.result !== undefined && (
                <div>
                  <div className="text-xs font-medium mb-1 text-gray-900">Result:</div>
                  <div className="text-sm text-gray-800 bg-gray-50 p-2 rounded border border-gray-200 max-h-48 overflow-y-auto">
                    <pre className="whitespace-pre-wrap font-mono text-xs">
                      {typeof toolCall.result === 'string'
                        ? toolCall.result
                        : JSON.stringify(toolCall.result, null, 2)}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          ))}
        </CardContent>
      )}
    </Card>
  )
}
