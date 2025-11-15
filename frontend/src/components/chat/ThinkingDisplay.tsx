import { Brain } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'
import { Badge } from '../ui/badge'

interface ThinkingDisplayProps {
  steps: string[]
}

export function ThinkingDisplay({ steps }: ThinkingDisplayProps) {
  return (
    <Card className="bg-blue-50 border-blue-200">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm text-gray-900">
          <Brain className="h-4 w-4 text-blue-600" />
          Agent Thinking Process
          <Badge variant="secondary" className="ml-auto bg-white">
            {steps.length} steps
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ol className="space-y-2 text-sm">
          {steps.map((step, index) => (
            <li key={index} className="flex gap-2">
              <span className="font-medium text-blue-600">{index + 1}.</span>
              <span className="flex-1 text-gray-800">{step}</span>
            </li>
          ))}
        </ol>
      </CardContent>
    </Card>
  )
}

