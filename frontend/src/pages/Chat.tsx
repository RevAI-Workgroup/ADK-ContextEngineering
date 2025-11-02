import { ChatInterface } from '../components/chat/ChatInterface'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { Bot } from 'lucide-react'

export function Chat() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <Bot className="h-8 w-8 text-primary" />
          <h1 className="text-3xl font-bold">Agent Chat</h1>
          <Badge variant="secondary" className="ml-auto">
            Phase 1.5
          </Badge>
        </div>
        <p className="text-muted-foreground">
          Chat with the ADK agent powered by Google ADK
        </p>
      </div>

      {/* Available Tools Info */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Available Tools</CardTitle>
          <CardDescription>The agent can use these tools to assist you</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            <ToolBadge name="calculate" description="Math operations" />
            <ToolBadge name="count_words" description="Word counting" />
            <ToolBadge name="get_current_time" description="Time queries" />
            <ToolBadge name="analyze_text" description="Text analysis" />
          </div>
        </CardContent>
      </Card>

      {/* Chat Interface */}
      <ChatInterface useRealtime={false} />
    </div>
  )
}

interface ToolBadgeProps {
  name: string
  description: string
}

function ToolBadge({ name, description }: ToolBadgeProps) {
  return (
    <div className="p-2 rounded-md bg-secondary text-secondary-foreground">
      <div className="text-xs font-medium">{name}</div>
      <div className="text-xs text-muted-foreground">{description}</div>
    </div>
  )
}

