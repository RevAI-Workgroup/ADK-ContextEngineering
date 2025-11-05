import { useState, KeyboardEvent, useRef } from 'react'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { Send, Paperclip } from 'lucide-react'

interface ChatInputProps {
  onSend: (message: string) => void
  onFileUpload?: (file: File) => void
  disabled?: boolean
  placeholder?: string
  uploadingFile?: boolean
}

export function ChatInput({
  onSend,
  onFileUpload,
  disabled = false,
  placeholder = 'Type your message...',
  uploadingFile = false,
}: ChatInputProps) {
  const [input, setInput] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleSend = () => {
    if (input.trim() && !disabled) {
      onSend(input.trim())
      setInput('')
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file && onFileUpload) {
      onFileUpload(file)
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const handleUploadClick = () => {
    fileInputRef.current?.click()
  }

  return (
    <div className="flex gap-2">
      <Input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        className="flex-1"
      />
      {onFileUpload && (
        <>
          <input
            ref={fileInputRef}
            type="file"
            accept=".txt,.md"
            onChange={handleFileChange}
            className="hidden"
          />
          <Button
            onClick={handleUploadClick}
            disabled={disabled || uploadingFile}
            size="icon"
            variant="outline"
            title="Upload document"
          >
            <Paperclip className="h-4 w-4" />
          </Button>
        </>
      )}
      <Button onClick={handleSend} disabled={disabled || !input.trim()} size="icon">
        <Send className="h-4 w-4" />
      </Button>
    </div>
  )
}

