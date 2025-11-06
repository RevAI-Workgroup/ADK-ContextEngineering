import { Brain, MessageSquare, BarChart3, Home, Database } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarFooter,
  useSidebar,
} from '@/components/ui/sidebar'
import { ThemeToggle } from '../theme/ThemeToggle'

const navItems = [
  { path: '/', label: 'Home', icon: Home },
  { path: '/chat', label: 'Chat', icon: MessageSquare },
  { path: '/metrics', label: 'Metrics', icon: BarChart3 },
  { path: '/vector-store', label: 'Vector Store', icon: Database },
]

/**
 * Renders the application's sidebar containing the header, navigation menu, and footer with a theme toggle.
 *
 * The navigation highlights the active route based on the current location. Clicking a navigation link closes the sidebar.
 *
 * @returns A JSX element representing the application's sidebar layout with navigation and footer.
 */
export function AppSidebar() {
  const location = useLocation()
  const { setOpenMobile, setOpen, isMobile } = useSidebar()

  const handleLinkClick = () => {
    // Close the sidebar when a link is clicked
    // This project is desktop-only, so we always close desktop sidebar
    setOpen(false)
  }

  return (
    <Sidebar>
      <SidebarHeader className="border-b px-6 py-4">
        <div className="flex items-center gap-2">
          <Brain className="h-6 w-6 text-primary" />
          <div className="flex flex-col">
            <span className="text-lg font-bold">Context Engineering</span>
            <span className="text-xs text-muted-foreground">Phase 3</span>
          </div>
        </div>
      </SidebarHeader>
      
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Navigation</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => {
                const isActive = location.pathname === item.path
                return (
                  <SidebarMenuItem key={item.path}>
                    <SidebarMenuButton asChild isActive={isActive}>
                      <Link to={item.path} onClick={handleLinkClick}>
                        <item.icon className="h-4 w-4" />
                        <span>{item.label}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                )
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="border-t p-4">
        <div className="flex items-center justify-between">
          <div className="text-xs text-muted-foreground">
            Built with Google ADK & React
          </div>
          <ThemeToggle />
        </div>
      </SidebarFooter>
    </Sidebar>
  )
}
