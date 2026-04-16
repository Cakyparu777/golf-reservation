import { useRef, useEffect, useState } from 'react'
import { Send, Mic, Plus, Bot } from 'lucide-react'
import { useChat } from '../context/ChatContext'

const QUICK_ACTIONS = [
  { label: 'Book Tee Time', prompt: 'Help me book a tee time.' },
  { label: 'Good Weather Picks', prompt: 'Find me the best good-weather tee times this weekend for 2 players.' },
  { label: 'Best Recommendation', prompt: 'Recommend the best tee times tomorrow based on weather, value, and availability.' },
  { label: 'View Stats', prompt: 'Show me my recent golf stats.' },
]

export default function AssistantPage() {
  const { messages, showQuickActions, loading, sendMessage, setShowQuickActions } = useChat()
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
                <div className="bg-gray-100 rounded-2xl rounded-tl-sm px-4 py-3">
                  <p className="text-sm text-gray-800 leading-relaxed whitespace-pre-wrap">{msg.content}</p>
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

        {/* Quick actions shown only when no conversation yet */}
        {showQuickActions && (
          <div className="flex gap-2 pl-11 flex-wrap">
            {QUICK_ACTIONS.map((action) => (
              <button
                key={action.label}
                onClick={() => {
                  setShowQuickActions(false)
                  handleSend(action.prompt)
                }}
                className="border border-gray-300 rounded-full px-4 py-1.5 text-sm text-gray-700 hover:bg-gray-50 hover:border-gray-400 transition-colors"
              >
                {action.label}
              </button>
            ))}
          </div>
        )}

        {/* Loading indicator */}
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
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend(input)}
            disabled={loading}
          />
          <button className="text-gray-400 hover:text-gray-600">
            <Mic size={18} />
          </button>
          <button
            onClick={() => handleSend(input)}
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
