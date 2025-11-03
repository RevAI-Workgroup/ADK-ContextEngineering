import { Link, useLocation } from 'react-router-dom'
import { Brain, MessageSquare, BarChart3 } from 'lucide-react'
import { cn } from '@/lib/utils'

export function Header() {
  const location = useLocation()

  const navItems = [
    { path: '/', label: 'Home', icon: Brain },
    { path: '/chat', label: 'Chat', icon: MessageSquare },
    { path: '/metrics', label: 'Metrics', icon: BarChart3 },
  ]

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto flex h-16 items-center px-4">
        <div className="mr-8 flex items-center gap-2">
          <Brain className="h-6 w-6 text-primary" />
          <span className="text-xl font-bold">Context Engineering</span>
        </div>

        <nav className="flex flex-1 items-center gap-6">
          {navItems.map(({ path, label, icon: Icon }) => {
            const isActive = location.pathname === path
            return (
              <Link
                key={path}
                to={path}
                className={cn(
                  'flex items-center gap-2 text-sm font-medium transition-colors hover:text-primary',
                  isActive ? 'text-primary' : 'text-muted-foreground'
                )}
              >
                <Icon className="h-4 w-4" />
                {label}
              </Link>
            )
          })}
        </nav>

        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Phase 1.5</span>
        </div>
      </div>
    </header>
  )
}

