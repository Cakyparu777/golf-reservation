import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { ChatProvider } from './context/ChatContext'
import { ToastProvider } from './context/ToastContext'
import Sidebar from './components/Sidebar'
import MobileTabs from './components/MobileTabs'
import AssistantPage from './components/AssistantPage'
import TeeTimesPage from './components/TeeTimesPage'
import MyGolfPage from './components/MyGolfPage'
import SettingsPage from './components/SettingsPage'
import LoginPage from './components/LoginPage'
import SignupPage from './components/SignupPage'
import ToastContainer from './components/Toast'

export type Page = 'assistant' | 'teetimes' | 'mygolf' | 'settings'

export const pagePaths: Record<Page, string> = {
  assistant: '/assistant',
  teetimes: '/tee-times',
  mygolf: '/my-golf',
  settings: '/settings',
}

function AppShell() {
  const { user, authReady } = useAuth()
  const location = useLocation()

  if (!authReady) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface">
        <div className="text-sm font-semibold text-green-900">Loading your clubhouse...</div>
      </div>
    )
  }

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
    <div className="flex h-screen bg-surface overflow-hidden">
      <div className="sidebar-desktop">
        <Sidebar />
      </div>
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
      <MobileTabs />
      <ToastContainer />
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <ChatProvider>
        <ToastProvider>
          <AppShell />
        </ToastProvider>
      </ChatProvider>
    </AuthProvider>
  )
}
