import { Outlet } from 'react-router-dom'
import { AppSidebar } from './AppSidebar'
import { ErrorBoundary } from '../common/ErrorBoundary'
import { SidebarProvider, SidebarTrigger, SidebarInset, useSidebar } from '@/components/ui/sidebar'
import { useEffect } from 'react'

function LayoutContent() {
  const { setOpen, isMobile, open } = useSidebar()
  const SIDEBAR_WIDTH = 256 // 16rem in pixels

  useEffect(() => {
    if (isMobile) return // Don't enable hover behavior on mobile

    const handleMouseMove = (e: MouseEvent) => {
      // Open sidebar when mouse is within 20px of the left edge
      if (e.clientX <= 20) {
        setOpen(true)
      }
      // Close sidebar when mouse moves beyond the sidebar width and sidebar is open
      else if (open && e.clientX > SIDEBAR_WIDTH + 20) {
        setOpen(false)
      }
    }

    // Add mouse move listener to detect left edge hover
    window.addEventListener('mousemove', handleMouseMove)

    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
    }
  }, [setOpen, isMobile, open])

  return (
    <div className="flex min-h-screen w-full">
      <AppSidebar />
      <SidebarInset className="flex flex-1 flex-col">
        <header className="sticky top-0 z-10 flex h-14 items-center gap-4 border-b bg-background/95 px-6 backdrop-blur supports-[backdrop-filter]:bg-background/60">
          <SidebarTrigger />
        </header>
        <ErrorBoundary>
          <main className="flex-1 p-6">
            <Outlet />
          </main>
        </ErrorBoundary>
      </SidebarInset>
    </div>
  )
}

export function Layout() {
  return (
    <SidebarProvider defaultOpen={false}>
      <LayoutContent />
    </SidebarProvider>
  )
}

