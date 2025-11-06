import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { Message } from '../types/message.types'
import { ContextEngineeringConfig, createDefaultConfig } from '../types/config.types'

interface ChatContextType {
  messages: Message[]
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>
  isProcessing: boolean
  setIsProcessing: React.Dispatch<React.SetStateAction<boolean>>
  errorMessage: string
  setErrorMessage: React.Dispatch<React.SetStateAction<string>>
  selectedModel: string | null
  setSelectedModel: React.Dispatch<React.SetStateAction<string | null>>
  config: ContextEngineeringConfig
  setConfig: React.Dispatch<React.SetStateAction<ContextEngineeringConfig>>
  clearChat: () => void
}

const ChatContext = createContext<ChatContextType | undefined>(undefined)

const CONFIG_STORAGE_KEY = 'context_engineering_config'

export function ChatProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<Message[]>([])
  const [isProcessing, setIsProcessing] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string>('')
  const [selectedModel, setSelectedModel] = useState<string | null>(null)
  
  // Initialize config from localStorage or use default
  const [config, setConfig] = useState<ContextEngineeringConfig>(() => {
    try {
      const savedConfig = localStorage.getItem(CONFIG_STORAGE_KEY)
      if (savedConfig) {
        const parsed = JSON.parse(savedConfig)

        // Migration: Handle old 'rag' structure
        if (parsed.rag && !parsed.naive_rag) {
          console.log('Migrating old RAG config to naive_rag')
          const defaultConfig = createDefaultConfig()
          const { rag, ...rest } = parsed
          return {
            ...rest,
            naive_rag: rag,
            rag_tool: defaultConfig.rag_tool,
          }
        }

        // Ensure all required fields exist
        const defaultConfig = createDefaultConfig()
        return {
          ...defaultConfig,
          ...parsed,
          naive_rag: parsed.naive_rag || defaultConfig.naive_rag,
          rag_tool: parsed.rag_tool || defaultConfig.rag_tool,
        }
      }
    } catch (error) {
      console.error('Failed to load config from localStorage:', error)
    }
    return createDefaultConfig()
  })

  // Persist config to localStorage whenever it changes
  useEffect(() => {
    try {
      localStorage.setItem(CONFIG_STORAGE_KEY, JSON.stringify(config))
    } catch (error) {
      console.error('Failed to save config to localStorage:', error)
    }
  }, [config])

  const clearChat = () => {
    setMessages([])
    setErrorMessage('')
    setIsProcessing(false)
  }

  return (
    <ChatContext.Provider
      value={{
        messages,
        setMessages,
        isProcessing,
        setIsProcessing,
        errorMessage,
        setErrorMessage,
        selectedModel,
        setSelectedModel,
        config,
        setConfig,
        clearChat,
      }}
    >
      {children}
    </ChatContext.Provider>
  )
}

export function useChatContext() {
  const context = useContext(ChatContext)
  if (context === undefined) {
    throw new Error('useChatContext must be used within a ChatProvider')
  }
  return context
}

