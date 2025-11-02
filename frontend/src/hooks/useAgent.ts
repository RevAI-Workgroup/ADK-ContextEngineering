import { useState, useCallback, useRef } from 'react'
import { agentService } from '../services/agentService'
import { AgentResponse } from '../types/agent.types'

export function useAgent() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [response, setResponse] = useState<AgentResponse | null>(null)
  
  // Track the latest request to handle concurrent calls
  const abortControllerRef = useRef<AbortController | null>(null)
  const requestIdRef = useRef(0)

  const sendMessage = useCallback(
    async (message: string, sessionId?: string, includeThinking: boolean = true) => {
      // Cancel previous request if still pending
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }

      // Create new abort controller for this request
      const abortController = new AbortController()
      abortControllerRef.current = abortController

      // Increment and store request ID for this call
      const currentRequestId = ++requestIdRef.current

      setLoading(true)
      setError(null)
      setResponse(null)

      try {
        const result = await agentService.sendMessage(
          message,
          sessionId,
          includeThinking,
          abortController.signal
        )
        
        // Only update state if this is still the latest request
        if (currentRequestId === requestIdRef.current) {
          setResponse(result)
          return result
        }
        
        // If not the latest request, return result without updating state
        return result
      } catch (err: any) {
        // Ignore abort errors from cancelled requests
        if (err.name === 'AbortError' || err.name === 'CanceledError') {
          // Only clear loading if this was the latest request
          if (currentRequestId === requestIdRef.current) {
            setLoading(false)
          }
          throw err
        }
        
        // Only set error if this is still the latest request
        if (currentRequestId === requestIdRef.current) {
          const errorMessage = err.response?.data?.detail || err.message || 'Failed to send message'
          setError(errorMessage)
        }
        throw err
      } finally {
        // Only clear loading if this was the latest request
        if (currentRequestId === requestIdRef.current) {
          setLoading(false)
          abortControllerRef.current = null
        }
      }
    },
    []
  )

  const reset = useCallback(() => {
    setResponse(null)
    setError(null)
  }, [])

  return {
    loading,
    error,
    response,
    sendMessage,
    reset,
  }
}

