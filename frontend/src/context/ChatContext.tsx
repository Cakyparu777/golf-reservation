import { createContext, useContext, useState, useCallback, ReactNode, useEffect, useRef } from 'react'
import { useAuth } from './AuthContext'
import { readErrorMessage } from '../lib/api'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

interface ChatContextValue {
  messages: ChatMessage[]
  sessionId: string | null
  showQuickActions: boolean
  loading: boolean
  sendMessage: (text: string) => Promise<void>
  setShowQuickActions: (v: boolean) => void
}

const ChatContext = createContext<ChatContextValue | null>(null)

const SESSION_KEY = 'fe_chat_session'
const MESSAGES_KEY = 'fe_chat_messages'

const INITIAL_MESSAGES: ChatMessage[] = [
  {
    role: 'assistant',
    content:
      "Welcome back to the Clubhouse. I've reviewed your recent rounds around Tokyo, and your driving accuracy has improved by 12% this month.",
    timestamp: '9:41 AM',
  },
  {
    role: 'assistant',
    content:
      'Would you like me to suggest a training drill for your short game, or are you looking to book a new tee time for this weekend?',
    timestamp: '9:41 AM',
  },
]

function loadMessages(): ChatMessage[] {
  try {
    const raw = sessionStorage.getItem(MESSAGES_KEY)
    if (raw) return JSON.parse(raw)
  } catch {}
  return INITIAL_MESSAGES
}

function saveMessages(messages: ChatMessage[]) {
  try {
    sessionStorage.setItem(MESSAGES_KEY, JSON.stringify(messages))
  } catch {}
}

function now(): string {
  return new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
}

export function ChatProvider({ children }: { children: ReactNode }) {
  const { user, token } = useAuth()
  const [messages, setMessages] = useState<ChatMessage[]>(loadMessages)
  const [sessionId, setSessionId] = useState<string | null>(
    () => sessionStorage.getItem(SESSION_KEY)
  )
  const [showQuickActions, setShowQuickActions] = useState(
    () => sessionStorage.getItem(SESSION_KEY) === null
  )
  const [loading, setLoading] = useState(false)
  const lastIdentityRef = useRef<string | null>(null)

  const clearSession = useCallback(() => {
    sessionStorage.removeItem(SESSION_KEY)
    sessionStorage.removeItem(MESSAGES_KEY)
    setSessionId(null)
    setMessages(INITIAL_MESSAGES)
    setShowQuickActions(true)
  }, [])

  useEffect(() => {
    const identity = user?.email ?? null
    if (lastIdentityRef.current === null) {
      lastIdentityRef.current = identity
      if (!identity && !token) {
        clearSession()
      }
      return
    }

    if (lastIdentityRef.current !== identity) {
      clearSession()
    }

    lastIdentityRef.current = identity
  }, [clearSession, token, user?.email])

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim()) return

    setShowQuickActions(false)

    const userMsg: ChatMessage = { role: 'user', content: text, timestamp: now() }
    setMessages((prev) => {
      const next = [...prev, userMsg]
      saveMessages(next)
      return next
    })
    setLoading(true)

    try {
      if (!token) {
        throw new Error('Please sign in to use the assistant.')
      }

      const sid = sessionStorage.getItem(SESSION_KEY)
      const res = await fetch('/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          message: text,
          session_id: sid,
          user_name: user?.name ?? null,
          user_email: user?.email ?? null,
          home_area: user?.home_area ?? null,
          travel_mode: user?.travel_mode ?? null,
          max_travel_minutes: user?.max_travel_minutes ?? null,
        }),
      })

      if (!res.ok) {
        throw new Error(await readErrorMessage(res, 'Chat request failed.'))
      }

      const data = await res.json()

      sessionStorage.setItem(SESSION_KEY, data.session_id)
      setSessionId(data.session_id)

      const assistantMsg: ChatMessage = {
        role: 'assistant',
        content: data.reply,
        timestamp: now(),
      }
      setMessages((prev) => {
        const next = [...prev, assistantMsg]
        saveMessages(next)
        return next
      })
    } catch (err) {
      const errMsg: ChatMessage = {
        role: 'assistant',
        content: err instanceof Error
          ? err.message
          : "I'm having trouble connecting to the server. Please ensure the backend is running on port 8000.",
        timestamp: now(),
      }
      setMessages((prev) => {
        const next = [...prev, errMsg]
        saveMessages(next)
        return next
      })
    } finally {
      setLoading(false)
    }
  }, [token, user])

  return (
    <ChatContext.Provider
      value={{ messages, sessionId, showQuickActions, loading, sendMessage, setShowQuickActions }}
    >
      {children}
    </ChatContext.Provider>
  )
}

export function useChat() {
  const ctx = useContext(ChatContext)
  if (!ctx) throw new Error('useChat must be used inside ChatProvider')
  return ctx
}
