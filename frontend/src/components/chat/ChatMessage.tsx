import { Message } from '../../types/message.types'
import { Card, CardContent } from '../ui/card'
import { User, Bot, Clock } from 'lucide-react'
import { cn, formatTimestamp } from '@/lib/utils'
import { ThinkingDisplay } from './ThinkingDisplay'
import { ToolOutputDisplay } from './ToolOutputDisplay'

interface ChatMessageProps {
  message: Message
}

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

            {/* Timestamp */}
            <div
              className={cn(
                'mt-2 flex items-center gap-1 text-xs',
                isUser ? 'text-primary-foreground/70' : 'text-muted-foreground'
              )}
            >
              <Clock className="h-3 w-3" />
              <span>{formatTimestamp(message.timestamp)}</span>
            </div>
          </CardContent>
        </Card>

        {/* Thinking Steps */}
        {message.thinking && message.thinking.length > 0 && (
          <ThinkingDisplay steps={message.thinking} />
        )}

        {/* Tool Calls */}
        {message.toolCalls && message.toolCalls.length > 0 && (
          <ToolOutputDisplay toolCalls={message.toolCalls} />
        )}
      </div>
    </div>
  )
}

