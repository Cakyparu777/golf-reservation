import { useState } from 'react'
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

function AppInner() {
  const { user } = useAuth()
  const [activePage, setActivePage] = useState<Page>('assistant')
  const [authView, setAuthView] = useState<'login' | 'signup'>('login')

  if (!user) {
    return authView === 'login' ? (
      <LoginPage onSwitchToRegister={() => setAuthView('signup')} />
    ) : (
      <SignupPage onSwitchToLogin={() => setAuthView('login')} />
    )
  }

  return (
    <div className="flex h-screen bg-[#f4f6f0] overflow-hidden">
      <Sidebar activePage={activePage} onNavigate={setActivePage} />
      <main className="flex-1 overflow-auto">
        {activePage === 'assistant' && <AssistantPage />}
        {activePage === 'teetimes' && <TeeTimesPage />}
        {activePage === 'mygolf' && <MyGolfPage />}
        {activePage === 'settings' && <SettingsPage />}
      </main>
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <ChatProvider>
        <AppInner />
      </ChatProvider>
    </AuthProvider>
  )
}
