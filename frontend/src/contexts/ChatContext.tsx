import { createContext, useContext, useState, ReactNode } from 'react'
import { Message } from '../types/message.types'

interface ChatContextType {
  messages: Message[]
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>
  isProcessing: boolean
  setIsProcessing: React.Dispatch<React.SetStateAction<boolean>>
  errorMessage: string
  setErrorMessage: React.Dispatch<React.SetStateAction<string>>
  selectedModel: string | null
  setSelectedModel: React.Dispatch<React.SetStateAction<string | null>>
  clearChat: () => void
}

const ChatContext = createContext<ChatContextType | undefined>(undefined)

export function ChatProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<Message[]>([])
  const [isProcessing, setIsProcessing] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string>('')
  const [selectedModel, setSelectedModel] = useState<string | null>(null)

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

