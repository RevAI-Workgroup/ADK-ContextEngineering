import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { ThemeProvider } from './components/theme/ThemeProvider'
import { TooltipProvider } from './components/ui/tooltip'
import { ChatProvider } from './contexts/ChatContext'
import { Layout } from './components/layout/Layout'
import { Home } from './pages/Home'
import { Chat } from './pages/Chat'
import { Metrics } from './pages/Metrics'
import { NotFound } from './pages/NotFound'

function App() {
  return (
    <ThemeProvider defaultTheme="dark">
      <TooltipProvider>
        <ChatProvider>
          <Router>
            <Routes>
              <Route path="/" element={<Layout />}>
                <Route index element={<Home />} />
                <Route path="chat" element={<Chat />} />
                <Route path="metrics" element={<Metrics />} />
                <Route path="*" element={<NotFound />} />
              </Route>
            </Routes>
          </Router>
        </ChatProvider>
      </TooltipProvider>
    </ThemeProvider>
  )
}

export default App

