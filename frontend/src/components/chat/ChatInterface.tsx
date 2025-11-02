import { useState, useEffect, useRef } from 'react'
import { Card } from '../ui/card'
import { ChatInput } from './ChatInput'
import { ChatMessage } from './ChatMessage'
import { Message } from '../../types/message.types'
import { ToolCall } from '../../types/agent.types'
import { useWebSocket } from '../../hooks/useWebSocket'
import { useAgent } from '../../hooks/useAgent'

interface ChatInterfaceProps {
  useRealtime?: boolean
}

export function ChatInterface({ useRealtime = false }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [isProcessing, setIsProcessing] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string>('')

  // WebSocket for real-time streaming
  const { isConnected, events, connect, sendMessage: sendWsMessage, clearEvents } = useWebSocket()

  // HTTP for synchronous requests
  const { sendMessage: sendHttpMessage } = useAgent()

  // Track current streaming message being built
  const streamingMessageRef = useRef<{
    thinking: string[]
    toolCalls: ToolCall[]
    content: string
    messageId: string
  } | null>(null)

  // Process WebSocket events in real-time
  useEffect(() => {
    if (!useRealtime || events.length === 0) return

    events.forEach((event) => {
      switch (event.type) {
        case 'thinking': {
          // TypeScript now knows event.data is ThinkingEventData
          if (streamingMessageRef.current) {
            streamingMessageRef.current.thinking.push(event.data.message)
          }
          break
        }

        case 'tool_call': {
          // TypeScript now knows event.data is ToolCallEventData
          if (streamingMessageRef.current) {
            // Parse tool call message to extract structured data
            // Expected format: "tool_name: description" or just description
            const message = event.data.message
            const colonIndex = message.indexOf(':')
            
            const toolCall: ToolCall = colonIndex > 0 
              ? {
                  name: message.substring(0, colonIndex).trim(),
                  description: message.substring(colonIndex + 1).trim(),
                  timestamp: event.timestamp
                }
              : {
                  name: 'unknown',
                  description: message,
                  timestamp: event.timestamp
                }
            
            streamingMessageRef.current.toolCalls.push(toolCall)
          }
          break
        }

        case 'response': {
          // TypeScript now knows event.data is ResponseEventData
          if (streamingMessageRef.current) {
            // Update content from response data
            streamingMessageRef.current.content = event.data.response
            
            // Merge thinking steps if provided
            if (event.data.thinking_steps) {
              streamingMessageRef.current.thinking = event.data.thinking_steps
            }
            
            // Merge tool calls if provided
            if (event.data.tool_calls) {
              // Append new tool calls rather than replacing
              streamingMessageRef.current.toolCalls.push(...event.data.tool_calls)
            }
          }
          break
        }

        case 'complete': {
          // TypeScript now knows event.data is CompleteEventData
          // Finalize the streaming message and add it to chat
          if (streamingMessageRef.current) {
            const assistantMessage: Message = {
              id: streamingMessageRef.current.messageId,
              role: 'assistant',
              content: streamingMessageRef.current.content,
              thinking: streamingMessageRef.current.thinking.length > 0 
                ? streamingMessageRef.current.thinking 
                : undefined,
              toolCalls: streamingMessageRef.current.toolCalls.length > 0 
                ? streamingMessageRef.current.toolCalls 
                : undefined,
              timestamp: event.timestamp,
            }

            setMessages((prev) => [...prev, assistantMessage])
            streamingMessageRef.current = null
            setIsProcessing(false)
            clearEvents()
          }
          break
        }

        case 'error': {
          // TypeScript now knows event.data is ErrorEventData
          console.error('WebSocket error event:', event.data)
          const errorMsg = event.data.message || event.data.error || 'An error occurred during real-time processing.'
          setErrorMessage(errorMsg)
          streamingMessageRef.current = null
          setIsProcessing(false)
          clearEvents()
          break
        }
      }
    })
  }, [events, useRealtime, clearEvents])

  const handleSendMessage = async (content: string) => {
    // Clear any previous errors on retry
    setErrorMessage('')
    
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    }

    setMessages((prev) => [...prev, userMessage])
    setIsProcessing(true)

    try {
      if (useRealtime && !isConnected) {
        await connect()
      }

      if (useRealtime) {
        // Use WebSocket for real-time streaming
        // Initialize the streaming message container
        streamingMessageRef.current = {
          thinking: [],
          toolCalls: [],
          content: '',
          messageId: (Date.now() + 1).toString(), // +1 to be different from user message ID
        }
        
        const success = sendWsMessage(content, undefined, true) // Clear events for each new message
        if (!success) {
          // If sending failed, throw an error to be caught by the catch block
          throw new Error('WebSocket not connected')
        }
        // Note: isProcessing will be set to false in the useEffect when 'complete' event is received
      } else {
        // Use HTTP for synchronous request
        const response = await sendHttpMessage(content)

        const assistantMessage: Message = {
          id: Date.now().toString(),
          role: 'assistant',
          content: response.response,
          thinking: response.thinking_steps,
          toolCalls: response.tool_calls,
          timestamp: response.timestamp,
        }

        setMessages((prev) => [...prev, assistantMessage])
      }
    } catch (err) {
      console.error('Error sending message:', err)
      
      // Differentiate error types and set user-friendly messages
      let userFriendlyMessage = 'Failed to send message. Please try again.'
      
      if (err instanceof Error) {
        const errorMsg = err.message.toLowerCase()
        
        // WebSocket/Connection errors
        if (useRealtime) {
          if (errorMsg.includes('websocket') || errorMsg.includes('connect')) {
            userFriendlyMessage = 'Connection lost. Please check your network and try again.'
          } else if (errorMsg.includes('timeout')) {
            userFriendlyMessage = 'Request timed out. The server may be busy, please try again.'
          } else {
            userFriendlyMessage = 'Real-time messaging failed. Please try again or switch to standard mode.'
          }
        } 
        // HTTP/Message-send errors
        else {
          if (errorMsg.includes('network') || errorMsg.includes('fetch')) {
            userFriendlyMessage = 'Network error. Please check your connection and try again.'
          } else if (errorMsg.includes('timeout')) {
            userFriendlyMessage = 'Request timed out. Please try again in a moment.'
          } else if (errorMsg.includes('500') || errorMsg.includes('server')) {
            userFriendlyMessage = 'Server error. Please try again later.'
          } else if (errorMsg.includes('400') || errorMsg.includes('bad request')) {
            userFriendlyMessage = 'Invalid request. Please rephrase your message.'
          }
        }
      }
      
      setErrorMessage(userFriendlyMessage)
      
      // Clean up streaming ref if error occurred during WebSocket
      if (useRealtime && streamingMessageRef.current) {
        streamingMessageRef.current = null
      }
    } finally {
      // Only reset isProcessing for HTTP mode
      // For WebSocket, it's reset when 'complete' event is received
      if (!useRealtime) {
        setIsProcessing(false)
      }
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-12rem)] gap-4">
      {/* Error Banner */}
      {errorMessage && (
        <div className="bg-destructive/15 border border-destructive/50 rounded-lg p-3 flex items-start gap-2">
          <span className="text-destructive text-sm font-medium">⚠️</span>
          <div className="flex-1">
            <p className="text-sm text-destructive font-medium">{errorMessage}</p>
          </div>
          <button
            onClick={() => setErrorMessage('')}
            className="text-destructive/70 hover:text-destructive text-sm"
            aria-label="Dismiss error"
          >
            ✕
          </button>
        </div>
      )}
      
      {/* Custom Chat Display */}
      <Card className="flex-1 p-4 overflow-y-auto">
        <div className="space-y-4">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="text-2xl mb-2">🤖</div>
              <div className="text-lg font-medium mb-1">Hello! I am your Context Engineering agent.</div>
              <div className="text-sm text-muted-foreground">How can I help you today?</div>
            </div>
          ) : (
            messages.map((message) => (
              <ChatMessage key={message.id} message={message} />
            ))
          )}
          {isProcessing && (
            <div className="text-sm text-muted-foreground animate-pulse">Agent is thinking...</div>
          )}
        </div>
      </Card>

      {/* Custom Input */}
      <ChatInput onSend={handleSendMessage} disabled={isProcessing} />
    </div>
  )
}

