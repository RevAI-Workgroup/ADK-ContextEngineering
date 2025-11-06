import { useState, KeyboardEvent, useRef, ChangeEvent } from 'react'
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

/**
 * Renders a chat input with a text field, send button, and an optional file upload control.
 *
 * The input supports Enter to send (Shift+Enter inserts a newline). If `onFileUpload` is provided,
 * a hidden file picker and upload button are rendered; selected files are validated for extension
 * (`.txt`, `.md`) and a 10MB size limit before being passed to `onFileUpload`.
 *
 * @param onSend - Called with the trimmed message when the user sends a message
 * @param onFileUpload - Optional callback invoked with a validated File when a user selects a file
 * @param disabled - When true, disables all interactive controls
 * @param placeholder - Placeholder text shown in the input when empty
 * @param uploadingFile - When true, disables the upload button to indicate an ongoing upload
 * @returns The chat input JSX element
 */
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

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file && onFileUpload) {
      // Validate file type
      const allowedExtensions = ['.txt', '.md']
      const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase()
      if (!allowedExtensions.includes(fileExtension)) {
        alert('Please upload a .txt or .md file')
        return
      }
      
      // Validate file size (e.g., max 10MB)
      const maxSize = 10 * 1024 * 1024
      if (file.size > maxSize) {
        alert('File size must be less than 10MB')
        return
      }
      
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
