import { ChatInterface } from '../components/chat/ChatInterface'
import { ModelSelector } from '../components/chat/ModelSelector'
import { ConfigurationPanel } from '../components/chat/ConfigurationPanel'
import { RunHistory } from '../components/chat/RunHistory'
import { RunComparison } from '../components/chat/RunComparison'
import { Card, CardContent, CardHeader } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Switch } from '../components/ui/switch'
import { Label } from '../components/ui/label'
import { Bot, Trash2, XCircle, ChevronDown, ChevronUp, Zap } from 'lucide-react'
import { useChatContext } from '../contexts/ChatContext'
import { modelsService } from '../services/modelsService'
import { agentService } from '../services/agentService'
import { useState, useEffect, useRef } from 'react'
import { Alert, AlertDescription } from '../components/ui/alert'
import { ContextEngineeringConfig } from '../types/config.types'
import { cn } from '../lib/utils'
import { Tool } from '../types/agent.types'

export function Chat() {
  const { clearChat, messages, config, setConfig, tokenStreamingEnabled, setTokenStreamingEnabled } = useChatContext()
  const [isClearing, setIsClearing] = useState(false)
  const [clearMessage, setClearMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)
  const [rerunMessage, setRerunMessage] = useState<{ query: string } | null>(null)
  const [isToolsExpanded, setIsToolsExpanded] = useState(false)
  const [showConfigPanel, setShowConfigPanel] = useState(false)
  const [showRunHistory, setShowRunHistory] = useState(false)
  const [comparisonRunIds, setComparisonRunIds] = useState<string[]>([])
  const [showComparison, setShowComparison] = useState(false)
  const [availableTools, setAvailableTools] = useState<Tool[]>([])
  const [activeTools, setActiveTools] = useState<Set<string>>(new Set())
  const configPanelRef = useRef<HTMLDivElement>(null)
  const configButtonRef = useRef<HTMLButtonElement>(null)

  // Fetch available tools when config changes
  useEffect(() => {
    let cancelled = false

    const fetchTools = async () => {
      try {
        const tools = await agentService.getTools(config)
        // Only update state if this effect hasn't been cancelled
        if (!cancelled) {
          setAvailableTools(tools)
        }
      } catch (error) {
        console.error('Failed to fetch tools:', error)
        // Only update state if this effect hasn't been cancelled
        if (!cancelled) {
          setAvailableTools([])
        }
      }
    }

    fetchTools()

    // Cleanup function to mark this request as cancelled
    return () => {
      cancelled = true
    }
  }, [config])

  // Auto-dismiss success messages after 5 seconds with proper cleanup
  useEffect(() => {
    if (clearMessage?.type === 'success') {
      const timer = setTimeout(() => setClearMessage(null), 5000)
      return () => clearTimeout(timer)
    }
  }, [clearMessage])

  // Auto-dismiss rerun messages after 10 seconds with proper cleanup
  useEffect(() => {
    if (rerunMessage) {
      const timer = setTimeout(() => setRerunMessage(null), 10000)
      return () => clearTimeout(timer)
    }
  }, [rerunMessage])

  // Handle click outside configuration panel
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        showConfigPanel &&
        configPanelRef.current &&
        configButtonRef.current &&
        !configPanelRef.current.contains(event.target as Node) &&
        !configButtonRef.current.contains(event.target as Node)
      ) {
        setShowConfigPanel(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showConfigPanel])

  // Track active tools from messages and auto-expand
  useEffect(() => {
    const toolsUsed = new Set<string>()
    
    // Collect all tools used in the current conversation
    messages.forEach(message => {
      if (message.toolCalls && message.toolCalls.length > 0) {
        message.toolCalls.forEach(toolCall => {
          const toolName = toolCall.name.toLowerCase().trim()
          toolsUsed.add(toolName)
          console.log('[Chat] Tool used:', toolName, 'from message:', message.id)
        })
      }
    })

    console.log('[Chat] Active tools:', Array.from(toolsUsed))
    setActiveTools(toolsUsed)
    
    // Auto-expand if any tools are being used
    if (toolsUsed.size > 0) {
      setIsToolsExpanded(true)
    }
  }, [messages])

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

  const handleCompareRuns = (runIds: string[]) => {
    setComparisonRunIds(runIds)
    setShowComparison(true)
  }

  const handleRerunWithConfig = (query: string, newConfig: ContextEngineeringConfig) => {
    setConfig(newConfig)
    // Show notification to inform user that config has been applied
    setRerunMessage({ query })
    // Scroll to top so user sees the message
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  return (
    <div className="flex gap-6 p-6">
      {/* Left Sidebar - Configuration & Run History */}
      <div className="w-80 space-y-4">
        <Button
          ref={configButtonRef}
          variant={showConfigPanel ? 'default' : 'outline'}
          className="w-full"
          onClick={() => setShowConfigPanel(!showConfigPanel)}
        >
          {showConfigPanel ? 'Hide' : 'Show'} Configuration
        </Button>
        
        {showConfigPanel && (
          <div 
            ref={configPanelRef}
            className="max-h-[calc(100vh-250px)] overflow-y-auto overflow-x-hidden"
          >
            <ConfigurationPanel
              config={config}
              onConfigChange={setConfig}
            />
          </div>
        )}
        
        <Button
          variant={showRunHistory ? 'default' : 'outline'}
          className="w-full"
          onClick={() => setShowRunHistory(!showRunHistory)}
        >
          {showRunHistory ? 'Hide' : 'Show'} Run History
        </Button>
        
        {showRunHistory && (
          <RunHistory
            onCompareRuns={handleCompareRuns}
            onRerunWithConfig={handleRerunWithConfig}
          />
        )}
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col space-y-6">
        {/* Page Header */}
        <div className="w-full">
          <div className="flex items-center justify-center gap-16 mb-2">
            <div className="flex items-center gap-2 flex-shrink-0">
              <Bot className="h-8 w-8 text-primary flex-shrink-0" />
              <h1 className="text-3xl font-bold whitespace-nowrap">Agent Chat</h1>
              <Badge variant="secondary" className="flex-shrink-0">
                Phase 3
              </Badge>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              {/* Token Streaming Toggle */}
              <div className="flex items-center gap-2 border rounded-lg px-3 py-2 bg-background hover:bg-accent/50 transition-colors">
                <Zap className={cn(
                  "h-4 w-4 transition-colors",
                  tokenStreamingEnabled ? "text-yellow-500" : "text-muted-foreground"
                )} />
                <Label 
                  htmlFor="token-streaming" 
                  className="text-sm cursor-pointer font-medium"
                  title="Enable real-time token streaming for faster visual feedback"
                >
                  Token Streaming
                </Label>
                <Switch
                  id="token-streaming"
                  checked={tokenStreamingEnabled}
                  onCheckedChange={setTokenStreamingEnabled}
                />
              </div>
              
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
          <Alert variant={clearMessage.type === 'error' ? 'destructive' : 'default'} className="w-full">
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

        {/* Rerun Configuration Applied Message */}
        {rerunMessage && (
          <Alert className="w-full border-blue-500 bg-blue-50 dark:bg-blue-950">
            <AlertDescription className="flex items-center justify-between">
              <div className="flex flex-col gap-1">
                <span className="font-semibold">Configuration applied from previous run</span>
                <span className="text-sm text-muted-foreground">
                  Original query: "{rerunMessage.query.substring(0, 80)}{rerunMessage.query.length > 80 ? '...' : ''}"
                </span>
                <span className="text-sm text-muted-foreground">
                  You can now send your query below with the loaded configuration.
                </span>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 -mr-2 flex-shrink-0"
                onClick={() => setRerunMessage(null)}
                aria-label="Dismiss message"
              >
                <XCircle className="h-4 w-4" />
              </Button>
            </AlertDescription>
          </Alert>
        )}

        {/* Available Tools Info */}
        <div className="flex justify-center w-full">
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
                  {availableTools.length > 0 ? (
                    availableTools.map((tool) => {
                      const toolNameLower = tool.name.toLowerCase().trim()
                      const isActive = activeTools.has(toolNameLower)
                      return (
                        <ToolBadge 
                          key={tool.name} 
                          name={tool.name} 
                          description={tool.description}
                          isActive={isActive}
                        />
                      )
                    })
                  ) : (
                    <p className="text-sm text-muted-foreground">No tools available</p>
                  )}
                </div>
              </CardContent>
            )}
          </Card>
        </div>

        {/* Chat Interface */}
        <div className="flex flex-col items-center w-full">
          <div className="w-full">
            <ChatInterface useRealtime={tokenStreamingEnabled} />
          </div>
        </div>
      </div>

      {/* Run Comparison Modal */}
      <RunComparison
        runIds={comparisonRunIds}
        open={showComparison}
        onOpenChange={setShowComparison}
      />
    </div>
  )
}

interface ToolBadgeProps {
  name: string
  isActive?: boolean
  description?: string
}

function ToolBadge({ name, isActive = false, description }: ToolBadgeProps) {
  return (
    <div 
      className={`px-2 py-1 rounded-md transition-colors duration-300 ${
        isActive 
          ? 'bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-100 border-2 border-green-500' 
          : 'bg-secondary text-secondary-foreground'
      }`}
    >
      <div className="text-xs font-medium">{name}</div>
    </div>
  )
}

