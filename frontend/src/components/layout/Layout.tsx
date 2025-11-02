import { Outlet } from 'react-router-dom'
import { Header } from './Header'
import { ErrorBoundary } from '../common/ErrorBoundary'

export function Layout() {
  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <ErrorBoundary>
        <main className="flex-1 container mx-auto px-4 py-8">
          <Outlet />
        </main>
      </ErrorBoundary>
      <footer className="border-t py-6">
        <div className="container mx-auto px-4 text-center text-sm text-muted-foreground">
          Context Engineering Sandbox - Phase 1.5 | Built with Google ADK, React & AG-UI
        </div>
      </footer>
    </div>
  )
}

