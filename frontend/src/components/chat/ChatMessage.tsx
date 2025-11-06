import { Message } from '../../types/message.types'
import { Card, CardContent } from '../ui/card'
import { User, Bot, Clock, Cpu } from 'lucide-react'
import { cn } from '@/lib/utils'
import { ThinkingDisplay } from './ThinkingDisplay'
import { ToolOutputDisplay } from './ToolOutputDisplay'
import { RAGFeedback } from './RAGFeedback'
import { Badge } from '../ui/badge'

interface ChatMessageProps {
  message: Message
}

/**
 * Render a chat message with avatar, content, timestamp, and contextual details.
 *
 * Renders a user-styled or assistant-styled message based on message.role. For assistant messages, conditionally shows a model badge when `message.model` exists, RAG feedback when `pipelineMetadata.rag_status === 'success'` and `rag_retrieved_docs > 0`, tool output when `message.toolCalls` is non-empty, and thinking steps when `message.thinking` is non-empty.
 *
 * @param message - The message to render, including role, content, timestamp, model, pipelineMetadata, toolCalls, and thinking steps.
 * @returns The rendered chat message element.
 */
export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user'

  return (
    <div className={cn('flex gap-3', isUser ? 'flex-row-reverse' : 'flex-row')}>
      {/* Avatar */}
      <div
        className={cn(
          'flex h-8 w-8 shrink-0 items-center justify-center rounded-full',
          isUser ? 'bg-primary text-primary-foreground' : 'bg-secondary text-secondary-foreground'
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      {/* Message Content */}
      <div className={cn('flex-1 space-y-2', isUser ? 'items-end' : 'items-start')}>
        {/* Main Message */}
        <Card className={cn(isUser ? 'bg-primary text-primary-foreground' : '')}>
          <CardContent className="p-3">
            <p className="text-sm whitespace-pre-wrap">{message.content}</p>

            {/* Timestamp and Model Info */}
            <div
              className={cn(
                'mt-2 flex items-center gap-3 text-xs',
                isUser ? 'text-primary-foreground/70' : 'text-muted-foreground'
              )}
            >
              <div className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                <span>
                  {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
              {!isUser && message.model && (
                <Badge variant="secondary" className="flex items-center gap-1 text-xs h-5 px-2">
                  <Cpu className="h-3 w-3" />
                  {message.model}
                </Badge>
              )}
            </div>
          </CardContent>
        </Card>

        {/* RAG Feedback - Show retrieval information only when RAG retrieved documents */}
        {!isUser && message.pipelineMetadata?.rag_status === 'success' && message.pipelineMetadata?.rag_retrieved_docs > 0 && (
          <RAGFeedback metadata={message.pipelineMetadata} />
        )}

        {/* Tool Calls */}
        {!isUser && message.toolCalls && message.toolCalls.length > 0 && (
          <ToolOutputDisplay toolCalls={message.toolCalls} />
        )}

        {/* Thinking Steps */}
        {!isUser && message.thinking && message.thinking.length > 0 && (
          <ThinkingDisplay steps={message.thinking} />
        )}
      </div>
    </div>
  )
}
