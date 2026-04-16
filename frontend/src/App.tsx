import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { ChatProvider } from './context/ChatContext'
import Sidebar from './components/Sidebar'
import AssistantPage from './components/AssistantPage'
import TeeTimesPage from './components/TeeTimesPage'
import MyGolfPage from './components/MyGolfPage'
import SettingsPage from './components/SettingsPage'
import LoginPage from './components/LoginPage'
import SignupPage from './components/SignupPage'

export type Page = 'assistant' | 'teetimes' | 'mygolf' | 'settings'

const pagePaths: Record<Page, string> = {
  assistant: '/assistant',
  teetimes: '/tee-times',
  mygolf: '/my-golf',
  settings: '/settings',
}

function AppShell() {
  const { user } = useAuth()
  const location = useLocation()

  if (!user) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="*" element={<Navigate to="/login" replace state={{ from: location }} />} />
      </Routes>
    )
  }

  return (
    <div className="flex h-screen bg-[#f4f6f0] overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <Routes>
          <Route path="/assistant" element={<AssistantPage />} />
          <Route path="/tee-times" element={<TeeTimesPage />} />
          <Route path="/my-golf" element={<MyGolfPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/login" element={<Navigate to={pagePaths.assistant} replace />} />
          <Route path="/signup" element={<Navigate to={pagePaths.assistant} replace />} />
          <Route path="/" element={<Navigate to={pagePaths.assistant} replace />} />
          <Route path="*" element={<Navigate to={pagePaths.assistant} replace />} />
        </Routes>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <ChatProvider>
        <AppShell />
      </ChatProvider>
    </AuthProvider>
  )
}
