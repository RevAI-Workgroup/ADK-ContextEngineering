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
        return JSON.parse(savedConfig)
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

