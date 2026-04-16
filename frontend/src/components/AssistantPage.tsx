import { useState, useRef, useEffect } from 'react'
import { Send, Mic, Plus, Bot } from 'lucide-react'

interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  isElite?: boolean
  card?: BookingCard
}

interface BookingCard {
  month: string
  day: string
  title: string
  subtitle: string
}

const QUICK_ACTIONS = ['Book Tee Time', 'Short Game Drills', 'View Stats']

const INITIAL_MESSAGES: Message[] = [
  {
    role: 'assistant',
    content:
      "Welcome back to the Clubhouse. I've analyzed your recent performance at Pebble Beach. Your driving accuracy has improved by 12% this month.",
    timestamp: '9:41 AM',
  },
  {
    role: 'assistant',
    content:
      'Would you like me to suggest a training drill for your short game, or are you looking to book a new tee time for this weekend?',
    timestamp: '9:41 AM',
  },
]

function now(): string {
  return new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
}

export default function AssistantPage() {
  const [messages, setMessages] = useState<Message[]>(INITIAL_MESSAGES)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [showQuickActions, setShowQuickActions] = useState(true)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function sendMessage(text: string) {
    if (!text.trim()) return
    setShowQuickActions(false)
    setInput('')

    const userMsg: Message = { role: 'user', content: text, timestamp: now() }
    setMessages((prev) => [...prev, userMsg])
    setLoading(true)

    try {
      const res = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          session_id: sessionId,
          user_name: 'Pro',
        }),
      })

      if (!res.ok) throw new Error('Network error')

      const data = await res.json()
      setSessionId(data.session_id)

      const assistantMsg: Message = {
        role: 'assistant',
        content: data.reply,
        timestamp: now(),
      }
      setMessages((prev) => [...prev, assistantMsg])
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: "I'm having trouble connecting to the server. Please ensure the backend is running on port 8000.",
          timestamp: now(),
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Hero Header */}
      <div
        className="relative h-52 bg-cover bg-center shrink-0"
        style={{
          backgroundImage:
            "url('https://images.unsplash.com/photo-1587174486073-ae5e5cff23aa?w=1200&q=80')",
        }}
      >
        <div className="absolute inset-0 bg-gradient-to-b from-white/10 via-transparent to-white/80" />
        <div className="absolute bottom-5 left-8">
          <span className="bg-[#c8922a] text-white text-[10px] font-bold uppercase tracking-widest px-3 py-1 rounded-full">
            Premium Assistant
          </span>
          <h1 className="text-4xl font-extrabold text-[#1a3d2b] mt-1 drop-shadow-sm">
            Good morning, Pro
          </h1>
          <p className="text-sm text-gray-700 mt-0.5">
            Your digital caddie is ready. Shall we review your upcoming rounds or analyze your recent stats?
          </p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-8 py-5 space-y-4">
        {messages.map((msg, i) => (
          <div key={i}>
            {msg.role === 'assistant' ? (
              <div className="flex gap-3 max-w-2xl">
                <div className="w-8 h-8 rounded-full bg-[#1a3d2b] flex items-center justify-center shrink-0 mt-0.5">
                  <Bot size={14} color="white" />
                </div>
                <div className="space-y-1">
                  {msg.isElite && (
                    <p className="text-[10px] font-bold text-[#c8922a] uppercase tracking-widest flex items-center gap-1">
                      <span>★</span> Elite Recommendation
                    </p>
                  )}
                  <div className="bg-gray-100 rounded-2xl rounded-tl-sm px-4 py-3">
                    <p className="text-sm text-gray-800 leading-relaxed">{msg.content}</p>
                  </div>
                  {msg.card && (
                    <div className="bg-white border border-gray-200 rounded-xl px-4 py-3 flex items-center justify-between mt-2 shadow-sm">
                      <div className="flex items-center gap-3">
                        <div className="text-center">
                          <p className="text-[10px] uppercase text-gray-400 font-semibold">{msg.card.month}</p>
                          <p className="text-xl font-bold text-gray-900">{msg.card.day}</p>
                        </div>
                        <div>
                          <p className="text-sm font-semibold text-gray-900">{msg.card.title}</p>
                          <p className="text-xs text-gray-500">{msg.card.subtitle}</p>
                        </div>
                      </div>
                      <button className="text-sm font-semibold text-[#1a3d2b] hover:underline">
                        Confirm
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="flex justify-end gap-2 items-end">
                <div className="max-w-sm">
                  <div className="bg-[#1a3d2b] text-white rounded-2xl rounded-br-sm px-4 py-3">
                    <p className="text-sm leading-relaxed">{msg.content}</p>
                  </div>
                  <p className="text-[10px] text-gray-400 text-right mt-1">Read {msg.timestamp}</p>
                </div>
                <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center shrink-0">
                  <span className="text-xs text-gray-600 font-semibold">P</span>
                </div>
              </div>
            )}
          </div>
        ))}

        {/* Quick actions after initial messages */}
        {showQuickActions && (
          <div className="flex gap-2 pl-11 flex-wrap">
            {QUICK_ACTIONS.map((action) => (
              <button
                key={action}
                onClick={() => sendMessage(action)}
                className="border border-gray-300 rounded-full px-4 py-1.5 text-sm text-gray-700 hover:bg-gray-50 hover:border-gray-400 transition-colors"
              >
                {action}
              </button>
            ))}
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="flex gap-3 max-w-2xl">
            <div className="w-8 h-8 rounded-full bg-[#1a3d2b] flex items-center justify-center shrink-0">
              <Bot size={14} color="white" />
            </div>
            <div className="bg-gray-100 rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-1">
              <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:0ms]" />
              <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:150ms]" />
              <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:300ms]" />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input Bar */}
      <div className="px-8 pb-6 pt-3 shrink-0">
        <div className="flex items-center gap-3 bg-white border border-gray-200 rounded-2xl px-4 py-3 shadow-sm">
          <button className="text-gray-400 hover:text-gray-600">
            <Plus size={18} />
          </button>
          <input
            className="flex-1 text-sm outline-none placeholder-gray-400 text-gray-800"
            placeholder="Type your message to GolfBot..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage(input)}
            disabled={loading}
          />
          <button className="text-gray-400 hover:text-gray-600">
            <Mic size={18} />
          </button>
          <button
            onClick={() => sendMessage(input)}
            disabled={!input.trim() || loading}
            className="w-8 h-8 bg-[#1a3d2b] rounded-full flex items-center justify-center disabled:opacity-40 hover:bg-[#1e4d33] transition-colors"
          >
            <Send size={14} color="white" />
          </button>
        </div>
      </div>
    </div>
  )
}
