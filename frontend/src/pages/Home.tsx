import { Link } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Brain, MessageSquare, BarChart3, ArrowRight } from 'lucide-react'

export function Home() {
  return (
    <div className="space-y-8">
      {/* Hero Section */}
      <div className="text-center space-y-4">
        <h1 className="text-4xl font-bold tracking-tight">
          Context Engineering Sandbox
        </h1>
        <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
          A demonstration platform showcasing progressive gains of context engineering techniques
          in LLM applications using Google ADK.
        </p>
      </div>

      {/* Feature Cards */}
      <div className="grid gap-6 md:grid-cols-3">
        <Card>
          <CardHeader>
            <Brain className="h-12 w-12 text-primary mb-4" />
            <CardTitle>ADK Agent</CardTitle>
            <CardDescription>
              Powered by Google ADK with tool calling capabilities and intelligent reasoning
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm">
              <li>✓ 4 integrated tools</li>
              <li>✓ Thinking process visibility</li>
              <li>✓ Context-aware responses</li>
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <MessageSquare className="h-12 w-12 text-primary mb-4" />
            <CardTitle>Interactive Chat</CardTitle>
            <CardDescription>
              Chat interface with real-time streaming and AG-UI protocol integration
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm">
              <li>✓ WebSocket streaming</li>
              <li>✓ Tool call visualization</li>
              <li>✓ Thinking steps display</li>
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <BarChart3 className="h-12 w-12 text-primary mb-4" />
            <CardTitle>Metrics Dashboard</CardTitle>
            <CardDescription>
              Track and compare performance across different context engineering phases
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm">
              <li>✓ Real-time metrics</li>
              <li>✓ Phase comparisons</li>
              <li>✓ Visual analytics</li>
            </ul>
          </CardContent>
        </Card>
      </div>

      {/* Project Phases */}
      <Card>
        <CardHeader>
          <CardTitle>Project Phases</CardTitle>
          <CardDescription>
            Progressive implementation of context engineering techniques
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <PhaseItem
              phase="Phase 0"
              title="Foundation & Benchmarking"
              status="complete"
              description="Evaluation framework and baseline metrics"
            />
            <PhaseItem
              phase="Phase 1"
              title="MVP Agent with Google ADK"
              status="complete"
              description="Basic agentic system with tool calling"
            />
            <PhaseItem
              phase="Phase 1.5"
              title="Web UI Development"
              status="current"
              description="React frontend with AG-UI integration"
            />
            <PhaseItem
              phase="Phase 2"
              title="Basic RAG Implementation"
              status="upcoming"
              description="Vector database and retrieval-augmented generation"
            />
          </div>
        </CardContent>
      </Card>

      {/* CTA */}
      <div className="flex justify-center gap-4">
        <Link to="/chat">
          <Button size="lg">
            Start Chatting
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        </Link>
        <Link to="/metrics">
          <Button size="lg" variant="outline">
            View Metrics
          </Button>
        </Link>
      </div>
    </div>
  )
}

interface PhaseItemProps {
  phase: string
  title: string
  status: 'complete' | 'current' | 'upcoming'
  description: string
}

function PhaseItem({ phase, title, status, description }: PhaseItemProps) {
  const statusColors = {
    complete: 'bg-green-500',
    current: 'bg-blue-500',
    upcoming: 'bg-gray-300',
  }

  const statusLabels = {
    complete: 'Complete',
    current: 'In Progress',
    upcoming: 'Upcoming',
  }

  return (
    <div className="flex gap-4 items-start">
      <div
        className={`flex-shrink-0 h-2 w-2 mt-2 rounded-full ${statusColors[status]}`}
        aria-label={statusLabels[status]}
      />
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className="font-medium">{phase}:</span>
          <span>{title}</span>
          <span className="text-xs text-muted-foreground ml-auto">{statusLabels[status]}</span>
        </div>
        <p className="text-sm text-muted-foreground mt-1">{description}</p>
      </div>
    </div>
  )
}

