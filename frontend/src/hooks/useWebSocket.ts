import { useState, useEffect, useCallback, useRef } from 'react'
import { StreamEvent } from '../types/message.types'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'

interface UseWebSocketOptions {
  /**
   * If true (default), preserves event history when sending messages.
   * If false, events are cleared only if explicitly requested per message.
   */
  preserveEvents?: boolean
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const { preserveEvents = true } = options
  const [isConnected, setIsConnected] = useState(false)
  const [events, setEvents] = useState<StreamEvent[]>([])
  const [error, setError] = useState<string | null>(null)
  const ws = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<number | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const isIntentionalCloseRef = useRef(false)

  // Reconnection config
  const INITIAL_RETRY_DELAY = 1000 // 1 second
  const MAX_RETRY_DELAY = 30000 // 30 seconds
  const MAX_RECONNECT_ATTEMPTS = 10

  const cleanupWebSocket = useCallback((socket: WebSocket | null) => {
    if (socket) {
      // Remove all event handlers to prevent memory leaks
      socket.onopen = null
      socket.onmessage = null
      socket.onerror = null
      socket.onclose = null
      
      // Close the socket if it's not already closed
      if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
        socket.close()
      }
    }
  }, [])

  const connect = useCallback(() => {
    // Prevent duplicate connections - check if socket exists and is already open/connecting
    if (ws.current) {
      const state = ws.current.readyState
      if (state === WebSocket.OPEN || state === WebSocket.CONNECTING) {
        console.log('[WebSocket] Already connected or connecting, skipping duplicate connection')
        return
      }
      // If socket exists but is not OPEN/CONNECTING, clean it up first
      cleanupWebSocket(ws.current)
      ws.current = null
    }

    // Clear any pending reconnection timers
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }

    isIntentionalCloseRef.current = false

    try {
      console.log('[WebSocket] Creating new connection...')
      ws.current = new WebSocket(`${WS_URL}/api/chat/ws`)

      ws.current.onopen = () => {
        console.log('[WebSocket] Connected')
        setIsConnected(true)
        setError(null)
        // Reset reconnection attempts on successful connection
        reconnectAttemptsRef.current = 0
        isIntentionalCloseRef.current = false
      }

      ws.current.onmessage = (event) => {
        try {
          const data: StreamEvent = JSON.parse(event.data)
          console.log('[WebSocket] Message received:', data.type)
          setEvents((prev) => [...prev, data])
        } catch (err) {
          console.error('[WebSocket] Error parsing message:', err)
        }
      }

      ws.current.onerror = (error) => {
        console.error('[WebSocket] Error:', error)
        setError('WebSocket connection error')
      }

      ws.current.onclose = (event) => {
        console.log('[WebSocket] Disconnected', event.code, event.reason)
        setIsConnected(false)
        
        // Schedule reconnection if not intentional close
        if (!isIntentionalCloseRef.current) {
          scheduleReconnect()
        }
      }
    } catch (err) {
      console.error('[WebSocket] Connection error:', err)
      setError('Failed to connect to WebSocket')
      scheduleReconnect()
    }
  }, [cleanupWebSocket])

  const scheduleReconnect = useCallback(() => {
    // Don't reconnect if it was an intentional disconnect or max attempts reached
    if (isIntentionalCloseRef.current || reconnectAttemptsRef.current >= MAX_RECONNECT_ATTEMPTS) {
      if (reconnectAttemptsRef.current >= MAX_RECONNECT_ATTEMPTS) {
        console.warn('[WebSocket] Max reconnection attempts reached')
        setError('Unable to connect after multiple attempts')
      }
      return
    }

    // Calculate exponential backoff delay
    const delay = Math.min(
      INITIAL_RETRY_DELAY * Math.pow(2, reconnectAttemptsRef.current),
      MAX_RETRY_DELAY
    )

    console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current + 1})`)

    reconnectTimeoutRef.current = window.setTimeout(() => {
      reconnectAttemptsRef.current += 1
      connect()
    }, delay) as unknown as number
  }, [connect])

  const disconnect = useCallback(() => {
    console.log('[WebSocket] Intentional disconnect')
    isIntentionalCloseRef.current = true
    
    // Clear any pending reconnection timers
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }

    // Clean up and close the WebSocket
    if (ws.current) {
      cleanupWebSocket(ws.current)
      ws.current = null
    }

    // Reset reconnection attempts
    reconnectAttemptsRef.current = 0
    setIsConnected(false)
  }, [cleanupWebSocket])

  const sendMessage = useCallback((
    message: string, 
    sessionId?: string, 
    clearEvents?: boolean
  ): boolean => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      const payload = {
        type: 'message',
        message,
        session_id: sessionId,
      }
      ws.current.send(JSON.stringify(payload))
      
      // Clear events only if explicitly requested via parameter,
      // or if preserveEvents is false and clearEvents is not explicitly set to false
      const shouldClear = clearEvents === true || (clearEvents === undefined && !preserveEvents)
      if (shouldClear) {
        setEvents([])
      }
      
      return true
    } else {
      console.error('[WebSocket] Not connected')
      setError('WebSocket not connected')
      return false
    }
  }, [preserveEvents])

  const clearEvents = useCallback(() => {
    setEvents([])
  }, [])

  useEffect(() => {
    return () => {
      // Cleanup on component unmount
      isIntentionalCloseRef.current = true
      
      // Clear any pending reconnection timers
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
        reconnectTimeoutRef.current = null
      }
      
      // Clean up and close the WebSocket
      if (ws.current) {
        cleanupWebSocket(ws.current)
        ws.current = null
      }
    }
  }, [cleanupWebSocket])

  return {
    isConnected,
    events,
    error,
    connect,
    disconnect,
    sendMessage,
    clearEvents,
  }
}

