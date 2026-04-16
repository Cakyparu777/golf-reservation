import { useRef, useEffect, useState } from 'react'
import { Send, Sparkles, Bot, Calendar, Cloud, Flag, Zap } from 'lucide-react'
import { useChat } from '../context/ChatContext'
import { useAuth } from '../context/AuthContext'
import ChatBubble from './ChatBubble'

const QUICK_ACTIONS = [
  { label: 'Book Tee Time', prompt: 'Help me book a tee time.', icon: Calendar, color: 'from-green-700 to-green-900' },
  { label: 'Good Weather Picks', prompt: 'Find me the best good-weather tee times this weekend for 2 players.', icon: Cloud, color: 'from-sky-500 to-sky-700' },
  { label: 'Best Recommendation', prompt: 'Recommend the best tee times tomorrow based on weather, value, and availability.', icon: Sparkles, color: 'from-gold-500 to-gold-400' },
  { label: 'My Reservations', prompt: 'Show me my upcoming reservations.', icon: Flag, color: 'from-emerald-500 to-emerald-700' },
]

function getGreeting(): string {
  const hour = new Date().getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 17) return 'Good afternoon'
  return 'Good evening'
}

export default function AssistantPage() {
  const { messages, showQuickActions, loading, sendMessage, setShowQuickActions } = useChat()
  const { user } = useAuth()
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  function handleSend(text: string) {
    if (!text.trim()) return
    setInput('')
    sendMessage(text)
  }

  const userName = user?.name?.split(' ')[0] ?? 'Pro'

  return (
    <div className="flex flex-col h-full">
      {/* Compact Header */}
      <div className="relative shrink-0 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-green-900 via-green-800 to-green-700 animate-gradientShift" />
        <div className="absolute inset-0 opacity-[.04]" style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
        }} />
        <div className="relative px-6 md:px-8 py-6 md:py-8">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-8 h-8 rounded-xl bg-white/10 flex items-center justify-center backdrop-blur-sm">
              <Zap size={14} className="text-gold-400" />
            </div>
            <span className="text-gold-400 text-[10px] font-bold uppercase tracking-[.15em]">
              AI Caddie
            </span>
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight animate-slideUp">
            {getGreeting()}, {userName}
          </h1>
          <p className="text-sm text-white/50 mt-1 animate-slideUp stagger-1">
            Your digital caddie is ready for today's round
          </p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 md:px-8 py-5 space-y-4">
        {messages.map((msg, i) => (
          <ChatBubble
            key={i}
            role={msg.role}
            content={msg.content}
            timestamp={msg.timestamp}
            userName={user?.name}
            index={i}
          />
        ))}

        {/* Quick actions */}
        {showQuickActions && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pl-0 md:pl-11 max-w-xl animate-slideUp stagger-2">
            {QUICK_ACTIONS.map((action, i) => {
              const Icon = action.icon
              return (
                <button
                  key={action.label}
                  onClick={() => {
                    setShowQuickActions(false)
                    handleSend(action.prompt)
                  }}
                  className={`flex items-center gap-3 bg-white border border-gray-100 rounded-2xl px-4 py-3 text-left hover:shadow-card hover:-translate-y-0.5 transition-all duration-200 animate-slideUp stagger-${i + 3}`}
                >
                  <div className={`w-9 h-9 rounded-xl bg-gradient-to-br ${action.color} flex items-center justify-center shrink-0`}>
                    <Icon size={15} color="white" />
                  </div>
                  <span className="text-sm font-medium text-gray-700">{action.label}</span>
                </button>
              )
            })}
          </div>
        )}

        {/* Typing indicator */}
        {loading && (
          <div className="flex gap-3 max-w-2xl animate-slideUp">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-green-900 to-green-700 flex items-center justify-center shrink-0 shadow-soft">
              <Bot size={14} color="white" />
            </div>
            <div className="bg-white rounded-2xl rounded-tl-md px-4 py-3.5 shadow-soft border border-gray-100/60 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 bg-gray-400 rounded-full typing-dot" />
              <span className="w-1.5 h-1.5 bg-gray-400 rounded-full typing-dot" />
              <span className="w-1.5 h-1.5 bg-gray-400 rounded-full typing-dot" />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input Bar */}
      <div className="px-4 md:px-8 pb-4 md:pb-6 pt-3 shrink-0">
        <div className="flex items-center gap-3 bg-white border border-gray-200/80 rounded-2xl px-4 py-3 shadow-soft focus-within:shadow-card focus-within:border-green-900/20 transition-all duration-200">
          <input
            id="chat-input"
            className="flex-1 text-sm outline-none placeholder-gray-400 text-gray-800 bg-transparent"
            placeholder="Ask your caddie anything..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend(input)}
            disabled={loading}
          />
          <button
            id="chat-send"
            onClick={() => handleSend(input)}
            disabled={!input.trim() || loading}
            className="w-9 h-9 bg-gradient-to-br from-green-900 to-green-700 rounded-xl flex items-center justify-center disabled:opacity-30 hover:shadow-glow transition-all duration-200 hover:scale-105 active:scale-95"
          >
            <Send size={14} color="white" />
          </button>
        </div>
        <p className="text-[10px] text-gray-300 text-center mt-2">
          GolfBot may occasionally provide inaccurate information. Verify important details.
        </p>
      </div>
    </div>
  )
}
