import { useEffect, useRef, useState } from 'react'
import { Card } from '../ui/card'
import { Alert, AlertDescription } from '../ui/alert'
import { Button } from '../ui/button'
import { X, AlertCircle } from 'lucide-react'
import { ChatInput } from './ChatInput'
import { ChatMessage } from './ChatMessage'
import { Message } from '../../types/message.types'
import { ToolCall } from '../../types/agent.types'
import { useWebSocket } from '../../hooks/useWebSocket'
import { useAgent } from '../../hooks/useAgent'
import { useChatContext } from '../../contexts/ChatContext'
import { uploadDocument } from '../../services/vectorStoreService'

interface ChatInterfaceProps {
  useRealtime?: boolean
}

export function ChatInterface({ useRealtime = false }: ChatInterfaceProps) {
  const { messages, setMessages, isProcessing, setIsProcessing, errorMessage, setErrorMessage, selectedModel, config, tokenStreamingEnabled } = useChatContext()
  const [uploadingFile, setUploadingFile] = useState(false)

  // WebSocket for real-time streaming
  const { isConnected, events, error: wsError, connect, sendMessage: sendWsMessage, clearEvents } = useWebSocket()

  // HTTP for synchronous requests
  const { sendMessage: sendHttpMessage } = useAgent()

  // Track current streaming message being built (standard mode)
  const streamingMessageRef = useRef<{
    thinking: string[]
    toolCalls: ToolCall[]
    content: string
    messageId: string
  } | null>(null)

  // Track streaming content for token streaming mode
  const [streamingContent, setStreamingContent] = useState<{
    reasoning: string
    response: string
    messageId: string
  } | null>(null)

  // Track last processed event to avoid re-processing on every update
  const lastProcessedEventIndex = useRef<number>(-1)

  // Track when we're in the process of establishing connection for a message send
  // This prevents false positive "connection lost" errors during initial connect
  const isConnectingRef = useRef<boolean>(false)

  // Track timeout for delayed disconnection error
  const disconnectionTimeoutRef = useRef<number | null>(null)

  // Cleanup disconnection timeout on unmount
  useEffect(() => {
    return () => {
      if (disconnectionTimeoutRef.current) {
        clearTimeout(disconnectionTimeoutRef.current)
      }
    }
  }, [])

  // Monitor WebSocket connection errors during processing
  useEffect(() => {
    if (useRealtime && wsError && isProcessing) {
      console.error('WebSocket error during processing:', wsError)
      // Default error message
      let errorMsg = 'Connection lost during streaming. The backend may have encountered an error. Check server logs for details.'
      
      // Try to extract more specific error from wsError if it's an object
      if (typeof wsError === 'object' && wsError !== null) {
        const wsErrorObj = wsError as any
        if (wsErrorObj.error) {
          errorMsg = wsErrorObj.error
          if (wsErrorObj.suggestion) {
            errorMsg += `\n\n💡 Suggestion: ${wsErrorObj.suggestion}`
          }
        }
      } else if (typeof wsError === 'string') {
        errorMsg = wsError
      }
      
      setErrorMessage(errorMsg)
      setIsProcessing(false)
      streamingMessageRef.current = null
      setStreamingContent(null)
    }
  }, [wsError, isProcessing, useRealtime, setErrorMessage, setIsProcessing])

  // Monitor WebSocket disconnections during processing
  // Uses a delay to prevent false positives during connection establishment or brief reconnects
  useEffect(() => {
    // Clear any pending timeout when dependencies change
    if (disconnectionTimeoutRef.current) {
      clearTimeout(disconnectionTimeoutRef.current)
      disconnectionTimeoutRef.current = null
    }

    // Don't show disconnection error if:
    // - Not using realtime mode
    // - WebSocket is connected
    // - Not currently processing
    // - Currently in the process of establishing initial connection
    if (!useRealtime || isConnected || !isProcessing || isConnectingRef.current) {
      return
    }

    // Add a delay before showing the disconnection error
    // This gives the WebSocket reconnection logic time to work
    // and prevents false positives during normal operation
    console.log('[ChatInterface] WebSocket disconnected during processing, waiting before showing error...')
    
    disconnectionTimeoutRef.current = window.setTimeout(() => {
      // Double-check conditions after the delay
      // The refs may have changed during the timeout
      if (!isConnectingRef.current) {
        console.warn('[ChatInterface] WebSocket disconnection confirmed after delay')
        setErrorMessage('Connection lost during streaming. Attempting to reconnect...')
      }
      disconnectionTimeoutRef.current = null
    }, 2000) // 2 second delay before showing error

    return () => {
      if (disconnectionTimeoutRef.current) {
        clearTimeout(disconnectionTimeoutRef.current)
        disconnectionTimeoutRef.current = null
      }
    }
  }, [isConnected, isProcessing, useRealtime, setErrorMessage])

  // Process WebSocket events in real-time
  useEffect(() => {
    if (!useRealtime || events.length === 0) return

    // Only process events that haven't been processed yet
    const newEvents = events.slice(lastProcessedEventIndex.current + 1)
    
    newEvents.forEach((event) => {
      // Debug logging for all event types
      console.log(`[ChatInterface] Processing event: ${event.type}`, {
        dataKeys: Object.keys(event.data || {}),
        tokenStreamingEnabled,
        hasStreamingContent: !!streamingContent
      })

      switch (event.type) {
        case 'token': {
          // Token streaming mode - accumulate response tokens
          if (tokenStreamingEnabled) {
            const tokenText = event.data.token
            console.log(`[ChatInterface] 📝 Response token (${tokenText.length} chars):`, tokenText.slice(0, 50))
            
            // Guard: early return if streamingContent is not initialized
            // This ensures we reuse the messageId from handleSendMessage
            setStreamingContent(prev => {
              if (!prev) {
                console.warn('[ChatInterface] Token event received before streamingContent initialization, ignoring')
                return null
              }
              return {
                reasoning: prev.reasoning,
                response: prev.response + tokenText,
                messageId: prev.messageId
              }
            })
          }
          break
        }

        case 'reasoning_token': {
          // Token streaming mode - accumulate reasoning tokens
          if (tokenStreamingEnabled) {
            const reasoningText = event.data.token
            console.log(`[ChatInterface] 🧠 Reasoning token (${reasoningText.length} chars):`, reasoningText.slice(0, 50))
            
            // Guard: early return if streamingContent is not initialized
            // This ensures we reuse the messageId from handleSendMessage
            setStreamingContent(prev => {
              if (!prev) {
                console.warn('[ChatInterface] Reasoning token event received before streamingContent initialization, ignoring')
                return null
              }
              const newReasoning = prev.reasoning + reasoningText
              console.log(`[ChatInterface] 🧠 Cumulative reasoning now ${newReasoning.length} chars`)
              return {
                reasoning: newReasoning,
                response: prev.response,
                messageId: prev.messageId
              }
            })
          }
          break
        }

        case 'thinking': {
          // Standard mode - TypeScript now knows event.data is ThinkingEventData
          if (!tokenStreamingEnabled && streamingMessageRef.current) {
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
          // Standard mode - TypeScript now knows event.data is ResponseEventData
          if (!tokenStreamingEnabled && streamingMessageRef.current) {
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
          console.log('[ChatInterface] ✅ COMPLETE event received', {
            model: event.data?.model,
            reasoning_length: event.data?.reasoning_length,
            response_length: event.data?.response_length,
            tokenStreamingEnabled,
            hasStreamingContent: !!streamingContent
          })
          
          // Clear any pending disconnection timeout since we completed successfully
          if (disconnectionTimeoutRef.current) {
            clearTimeout(disconnectionTimeoutRef.current)
            disconnectionTimeoutRef.current = null
          }
          
          if (tokenStreamingEnabled && streamingContent) {
            // Token streaming mode: use accumulated content
            const finalReasoning = (streamingContent.reasoning || '').trimEnd()
            const finalResponse = streamingContent.response.trimEnd()
            
            console.log('[ChatInterface] 📊 Final content summary:', {
              reasoningChars: finalReasoning.length,
              responseChars: finalResponse.length,
              reasoningPreview: finalReasoning.slice(0, 100),
              responsePreview: finalResponse.slice(0, 100)
            })
            
            const assistantMessage: Message = {
              id: streamingContent.messageId,
              role: 'assistant',
              content: finalResponse,
              reasoning: finalReasoning ? finalReasoning : undefined,
              timestamp: event.timestamp,
              model: event.data?.model || selectedModel || undefined,
              pipelineMetadata: event.data?.pipeline_metadata,
              pipelineMetrics: event.data?.pipeline_metrics,
              metrics: event.data?.enabled_techniques
                ? {
                    enabled_techniques: event.data.enabled_techniques,
                  }
                : undefined,
            }
            setMessages((prev) => [...prev, assistantMessage])
            setStreamingContent(null)
          } else if (streamingMessageRef.current) {
            // Standard mode: use ref content
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
              model: event.data?.model || selectedModel || undefined,
              pipelineMetadata: event.data?.pipeline_metadata,
              pipelineMetrics: event.data?.pipeline_metrics,
              metrics: event.data?.enabled_techniques
                ? {
                    enabled_techniques: event.data.enabled_techniques,
                  }
                : undefined,
            }
            setMessages((prev) => [...prev, assistantMessage])
            streamingMessageRef.current = null
          }
          
          setIsProcessing(false)
          lastProcessedEventIndex.current = -1 // Reset event tracking
          clearEvents()
          break
        }

        case 'error': {
          // TypeScript now knows event.data is ErrorEventData
          console.error('[ChatInterface] ❌ ERROR event received:', event.data)
          
          // Clear any pending disconnection timeout
          if (disconnectionTimeoutRef.current) {
            clearTimeout(disconnectionTimeoutRef.current)
            disconnectionTimeoutRef.current = null
          }
          
          // Build comprehensive error message
          let errorMsg = event.data.message || event.data.error || 'An error occurred during real-time processing.'
          
          // Add suggestion if available
          if (event.data.suggestion) {
            errorMsg += `\n\n💡 Suggestion: ${event.data.suggestion}`
          }
          
          // Add partial response if available (for partial failures)
          if (event.data.partial_response) {
            errorMsg += `\n\n📝 Partial response was received before the error occurred.`
          }
          
          setErrorMessage(errorMsg)
          streamingMessageRef.current = null
          setStreamingContent(null)
          setIsProcessing(false)
          lastProcessedEventIndex.current = -1 // Reset event tracking
          clearEvents()
          break
        }
      }
    })
    
    // Update the last processed index to the last event we just handled
    if (newEvents.length > 0) {
      lastProcessedEventIndex.current = events.length - 1
    }
  }, [events, useRealtime, tokenStreamingEnabled, streamingContent, clearEvents, setMessages, setErrorMessage, setIsProcessing, selectedModel])

  const handleSendMessage = async (content: string) => {
    // Clear any previous errors on retry
    setErrorMessage('')
    
    // Clear any pending disconnection timeout
    if (disconnectionTimeoutRef.current) {
      clearTimeout(disconnectionTimeoutRef.current)
      disconnectionTimeoutRef.current = null
    }
    
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
        // Mark that we're establishing initial connection
        // This prevents false "connection lost" errors
        isConnectingRef.current = true
        try {
          await connect()
        } finally {
          isConnectingRef.current = false
        }
      }

      if (useRealtime) {
        // Use WebSocket for real-time streaming
        if (tokenStreamingEnabled) {
          // Token streaming mode - initialize streaming content
          setStreamingContent({
            reasoning: '',
            response: '',
            messageId: (Date.now() + 1).toString(),
          })
        } else {
          // Standard mode - initialize the streaming message container
          streamingMessageRef.current = {
            thinking: [],
            toolCalls: [],
            content: '',
            messageId: (Date.now() + 1).toString(),
          }
        }
        
        const success = sendWsMessage(
          content, 
          selectedModel || undefined, 
          true,
          undefined,
          tokenStreamingEnabled,  // Pass streaming preference
          config  // Pass context engineering config
        )
        if (!success) {
          // If sending failed, throw an error to be caught by the catch block
          throw new Error('WebSocket not connected')
        }
        // Note: isProcessing will be set to false in the useEffect when 'complete' event is received
      } else {
        // Use HTTP for synchronous request
        const response = await sendHttpMessage(content, undefined, true, selectedModel, config)

        const assistantMessage: Message = {
          id: Date.now().toString(),
          role: 'assistant',
          content: response.response,
          thinking: response.thinking_steps,
          toolCalls: response.tool_calls,
          timestamp: response.timestamp,
          model: response.model,
          pipelineMetadata: response.pipeline_metadata,
          pipelineMetrics: response.pipeline_metrics,
          metrics: response.metrics,
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
      
      // Clean up streaming state if error occurred during WebSocket
      if (useRealtime) {
        if (streamingMessageRef.current) {
          streamingMessageRef.current = null
        }
        if (streamingContent) {
          setStreamingContent(null)
        }
        // Ensure connecting flag is reset
        isConnectingRef.current = false
      }
    } finally {
      // Only reset isProcessing for HTTP mode
      // For WebSocket, it's reset when 'complete' event is received
      if (!useRealtime) {
        setIsProcessing(false)
      }
    }
  }

  const handleFileUpload = async (file: File) => {
    if (!['.txt', '.md'].some(ext => file.name.endsWith(ext))) {
      setErrorMessage('Only .txt and .md files are supported')
      return
    }

    setUploadingFile(true)
    try {
      await uploadDocument(file)
      // Add a system message to chat
      const systemMessage: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: `✅ Document "${file.name}" uploaded successfully and added to vector store. You can now ask questions about its content!`,
        timestamp: new Date().toISOString()
      }
      setMessages(prev => [...prev, systemMessage])
    } catch (error) {
      console.error('Upload failed:', error)
      setErrorMessage(`Failed to upload document: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      setUploadingFile(false)
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-300px)] min-h-[500px] w-full gap-4">
      {/* Error Banner */}
      {errorMessage && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription className="flex items-center justify-between">
            <span>{errorMessage}</span>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 -mr-2"
              onClick={() => setErrorMessage('')}
              aria-label="Dismiss error"
            >
              <X className="h-4 w-4" />
            </Button>
          </AlertDescription>
        </Alert>
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
            <>
              {messages.map((message) => (
                <ChatMessage key={message.id} message={message} />
              ))}
              {/* Show streaming message while in progress */}
              {isProcessing && streamingContent && tokenStreamingEnabled && (
                <ChatMessage 
                  key="streaming" 
                  message={{
                    id: 'streaming',
                    role: 'assistant',
                    content: streamingContent.response,
                    reasoning: streamingContent.reasoning,
                    timestamp: new Date().toISOString()
                  }}
                  isStreaming={true}
                />
              )}
            </>
          )}
          {isProcessing && !tokenStreamingEnabled && (
            <div className="text-sm text-muted-foreground animate-pulse">Agent is thinking...</div>
          )}
        </div>
      </Card>

      {/* Custom Input */}
      <ChatInput
        onSend={handleSendMessage}
        onFileUpload={handleFileUpload}
        disabled={isProcessing}
        uploadingFile={uploadingFile}
      />
    </div>
  )
}

