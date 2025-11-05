import { Wrench } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'
import { Badge } from '../ui/badge'
import { ToolCall } from '../../types/agent.types'

interface ToolOutputDisplayProps {
  toolCalls: ToolCall[]
}

export function ToolOutputDisplay({ toolCalls }: ToolOutputDisplayProps) {
  return (
    <Card className="bg-accent/50">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm">
          <Wrench className="h-4 w-4 text-primary" />
          Tool Calls
          <Badge variant="secondary" className="ml-auto">
            {toolCalls.length}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {toolCalls?.map((toolCall, index) => (
            <div key={toolCall.timestamp || `tool-${index}`} className="rounded-md bg-background p-3 space-y-2">
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="font-mono text-xs">
                  {toolCall.name}
                </Badge>
                {toolCall.timestamp && (
                  <span className="text-xs text-muted-foreground">
                    {new Date(toolCall.timestamp).toLocaleTimeString()}
                  </span>
                )}
              </div>
              
              <p className="text-xs text-muted-foreground">{toolCall.description}</p>
              
              {toolCall.parameters && (
                <div className="mt-2">
                  <div className="text-xs font-medium mb-1">Parameters:</div>
                  <code className="text-xs block bg-muted p-2 rounded overflow-x-auto">
                    {JSON.stringify(toolCall.parameters, null, 2)}
                  </code>
                </div>
              )}
              
              {toolCall.result !== undefined && (
                <div className="mt-2">
                  <div className="text-xs font-medium mb-1">Result:</div>
                  <code className="text-xs block bg-muted p-2 rounded overflow-x-auto">
                    {typeof toolCall.result === 'string' 
                      ? toolCall.result 
                      : JSON.stringify(toolCall.result, null, 2)}
                  </code>
                </div>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

