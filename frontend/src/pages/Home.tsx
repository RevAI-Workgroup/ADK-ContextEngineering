import { Link } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Brain, MessageSquare, Server, ArrowRight } from 'lucide-react'

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
            <Server className="h-12 w-12 text-primary mb-4" />
            <CardTitle>Locally Hosted LLMs</CardTitle>
            <CardDescription>
              Powered by Ollama with complete privacy and offline capability
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm">
              <li>✓ 100% local processing</li>
              <li>✓ No data sent to external APIs</li>
              <li>✓ Full control over models</li>
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
              title="Foundation & Benchmarking Setup"
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
              status="complete"
              description="React frontend with AG-UI integration"
            />
            <PhaseItem
              phase="Phase 2"
              title="Modular Platform Infrastructure"
              status="complete"
              description="Toggleable architecture for technique comparison"
            />
            <PhaseItem
              phase="Phase 3"
              title="RAG Module Implementation"
              status="complete"
              description="Vector database and retrieval-augmented generation"
            />
            <PhaseItem
              phase="Phase 4"
              title="Compression & Caching Modules"
              status="current"
              description="Context compression and semantic caching"
            />
            <PhaseItem
              phase="Phase 5"
              title="Reranking & Hybrid Search"
              status="upcoming"
              description="Advanced retrieval techniques"
            />
            <PhaseItem
              phase="Phase 6"
              title="Advanced Technique Modules"
              status="upcoming"
              description="Graph RAG, adaptive chunking, query routing"
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
    complete: 'bg-green-500 dark:bg-green-600',
    current: 'bg-primary',
    upcoming: 'bg-muted-foreground/30',
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

