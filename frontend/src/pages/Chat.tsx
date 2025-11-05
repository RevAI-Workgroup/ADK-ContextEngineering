import { ChatInterface } from '../components/chat/ChatInterface'
import { ModelSelector } from '../components/chat/ModelSelector'
import { Card, CardContent, CardHeader } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Bot, Trash2, XCircle, ChevronDown, ChevronUp } from 'lucide-react'
import { useChatContext } from '../contexts/ChatContext'
import { modelsService } from '../services/modelsService'
import { useState, useEffect } from 'react'
import { Alert, AlertDescription } from '../components/ui/alert'

export function Chat() {
  const { clearChat, messages } = useChatContext()
  const [isClearing, setIsClearing] = useState(false)
  const [clearMessage, setClearMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)
  const [isToolsExpanded, setIsToolsExpanded] = useState(false)

  // Auto-dismiss success messages after 5 seconds with proper cleanup
  useEffect(() => {
    if (clearMessage?.type === 'success') {
      const timer = setTimeout(() => setClearMessage(null), 5000)
      return () => clearTimeout(timer)
    }
  }, [clearMessage])

  const handleClearModels = async () => {
    setIsClearing(true)
    setClearMessage(null)
    
    try {
      const result = await modelsService.clearRunningModels()
      
      if (result.success) {
        // Clear chat when models are successfully cleared
        clearChat()
        
        // Update message to reflect both actions
        const message = result.models_stopped.length > 0 
          ? `${result.message} and cleared chat`
          : result.message
        
        setClearMessage({
          type: 'success',
          text: message
        })
      } else {
        setClearMessage({
          type: 'error',
          text: result.message
        })
      }
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || 'Failed to clear models'
      setClearMessage({
        type: 'error',
        text: errorMsg
      })
    } finally {
      setIsClearing(false)
    }
  }

  return (
    <div className="flex flex-col items-center space-y-6">
      {/* Page Header */}
      <div className="w-full max-w-4xl">
        <div className="flex items-center gap-2 mb-2">
          <Bot className="h-8 w-8 text-primary" />
          <h1 className="text-3xl font-bold">Agent Chat</h1>
          <Badge variant="secondary" className="ml-2">
            Phase 1.5
          </Badge>
          <div className="ml-auto flex items-center gap-4">
            <ModelSelector />
            <Button
              variant="outline"
              size="sm"
              onClick={handleClearModels}
              disabled={isClearing}
              title="Unload all running models from memory and clear chat"
            >
              <XCircle className="h-4 w-4 mr-2" />
              {isClearing ? 'Clearing...' : 'Clear Models'}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={clearChat}
              disabled={messages.length === 0}
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Clear Chat
            </Button>
          </div>
        </div>
      </div>

      {/* Clear Models Status Message */}
      {clearMessage && (
        <Alert variant={clearMessage.type === 'error' ? 'destructive' : 'default'} className="w-full max-w-4xl">
          <AlertDescription className="flex items-center justify-between">
            <span>{clearMessage.text}</span>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 -mr-2"
              onClick={() => setClearMessage(null)}
              aria-label="Dismiss message"
            >
              <XCircle className="h-4 w-4" />
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* Available Tools Info */}
      <div className="flex justify-center w-full max-w-4xl">
        <Card className="inline-block">
          <CardHeader 
            className="cursor-pointer hover:bg-accent/50 transition-colors flex items-center justify-center py-3"
            onClick={() => setIsToolsExpanded(!isToolsExpanded)}
          >
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold">Available Tools</span>
              {isToolsExpanded ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </div>
          </CardHeader>
          {isToolsExpanded && (
            <CardContent className="pt-0">
              <div className="flex flex-wrap gap-2">
                <ToolBadge name="calculate" />
                <ToolBadge name="count_words" />
                <ToolBadge name="get_current_time" />
                <ToolBadge name="analyze_text" />
              </div>
            </CardContent>
          )}
        </Card>
      </div>

      {/* Chat Interface */}
      <ChatInterface useRealtime={false} />
    </div>
  )
}

interface ToolBadgeProps {
  name: string
}

function ToolBadge({ name }: ToolBadgeProps) {
  return (
    <div className="px-2 py-1 rounded-md bg-secondary text-secondary-foreground">
      <div className="text-xs font-medium">{name}</div>
    </div>
  )
}

