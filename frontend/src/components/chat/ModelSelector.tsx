import { useEffect, useState, useRef } from 'react'
import { Bot } from 'lucide-react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select'
import { modelsService, OllamaModel } from '../../services/modelsService'
import { useChatContext } from '../../contexts/ChatContext'

export function ModelSelector() {
  const [models, setModels] = useState<OllamaModel[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { selectedModel, setSelectedModel, clearChat } = useChatContext()
  const hasInitialized = useRef(false)

  useEffect(() => {
    const fetchModels = async () => {
      try {
        setIsLoading(true)
        setError(null)
        const data = await modelsService.getModels()
        setModels(data)
        
        // Auto-select model if none is selected and we haven't initialized yet
        if (data.length > 0 && !hasInitialized.current) {
          // Check current selectedModel state at the time of model fetch
          setSelectedModel((currentModel) => {
            // Only set default if no model is currently selected
            if (!currentModel) {
              // Prefer "qwen3:0.6b" if available, otherwise select the first model
              const preferredModel = data.find(model => model.name === 'qwen3:0.6b')
              return preferredModel ? preferredModel.name : data[0].name
            }
            return currentModel
          })
          hasInitialized.current = true
        }
      } catch (err) {
        console.error('Error fetching models:', err)
        setError('Failed to load models. Is Ollama running?')
      } finally {
        setIsLoading(false)
      }
    }

    fetchModels()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleValueChange = (value: string) => {
    // Check if model is actually changing
    if (selectedModel && value !== selectedModel) {
      // Clear chat when switching models
      clearChat()
    }
    setSelectedModel(value)
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 text-sm text-destructive">
        <Bot className="h-4 w-4" />
        <span>{error}</span>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="flex items-center gap-2">
        <Bot className="h-4 w-4 text-muted-foreground" />
        <span className="text-sm text-muted-foreground">Loading models...</span>
      </div>
    )
  }

  if (models.length === 0) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Bot className="h-4 w-4" />
        <span>No models available</span>
      </div>
    )
  }

  return (
    <div className="flex items-center gap-2">
      <Bot className="h-4 w-4 text-muted-foreground" />
      <Select value={selectedModel || undefined} onValueChange={handleValueChange}>
        <SelectTrigger className="w-[150px]">
          <SelectValue placeholder="Select a model" />
        </SelectTrigger>
        <SelectContent>
          {models.map((model) => (
            <SelectItem key={model.name} value={model.name}>
              {model.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}

