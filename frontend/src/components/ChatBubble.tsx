import { useState, type ReactNode } from 'react'
import { Bot, Copy, Check } from 'lucide-react'

interface Props {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  userName?: string
  index: number
}

/* ── Lightweight markdown renderer (no deps) ──────────────── */
function renderMarkdown(text: string): ReactNode[] {
  const lines = text.split('\n')
  const elements: ReactNode[] = []
  let listItems: ReactNode[] = []
  let listType: 'ul' | 'ol' | null = null
  let inCodeBlock = false
  let codeLines: string[] = []

  function flushList() {
    if (listItems.length > 0 && listType) {
      const Tag = listType
      elements.push(<Tag key={`list-${elements.length}`} className="my-1">{listItems}</Tag>)
      listItems = []
      listType = null
    }
  }

  function inlineFormat(line: string): ReactNode {
    // Bold + italic, bold, italic, inline code
    const parts: ReactNode[] = []
    const regex = /(\*\*\*(.+?)\*\*\*|\*\*(.+?)\*\*|\*(.+?)\*|`([^`]+)`)/g
    let last = 0
    let match: RegExpExecArray | null

    while ((match = regex.exec(line)) !== null) {
      if (match.index > last) {
        parts.push(line.slice(last, match.index))
      }
      if (match[2]) parts.push(<strong key={match.index} className="font-semibold"><em>{match[2]}</em></strong>)
      else if (match[3]) parts.push(<strong key={match.index} className="font-semibold">{match[3]}</strong>)
      else if (match[4]) parts.push(<em key={match.index}>{match[4]}</em>)
      else if (match[5]) parts.push(<code key={match.index}>{match[5]}</code>)
      last = match.index + match[0].length
    }
    if (last < line.length) parts.push(line.slice(last))
    return parts.length > 0 ? parts : line
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]

    // Code blocks
    if (line.trim().startsWith('```')) {
      if (inCodeBlock) {
        elements.push(
          <pre key={`code-${i}`} className="my-1">
            <code>{codeLines.join('\n')}</code>
          </pre>
        )
        codeLines = []
        inCodeBlock = false
      } else {
        flushList()
        inCodeBlock = true
      }
      continue
    }
    if (inCodeBlock) {
      codeLines.push(line)
      continue
    }

    // Unordered list
    const ulMatch = line.match(/^\s*[-*]\s+(.+)/)
    if (ulMatch) {
      if (listType !== 'ul') flushList()
      listType = 'ul'
      listItems.push(<li key={`li-${i}`}>{inlineFormat(ulMatch[1])}</li>)
      continue
    }

    // Ordered list
    const olMatch = line.match(/^\s*\d+\.\s+(.+)/)
    if (olMatch) {
      if (listType !== 'ol') flushList()
      listType = 'ol'
      listItems.push(<li key={`li-${i}`}>{inlineFormat(olMatch[1])}</li>)
      continue
    }

    flushList()

    // Empty line
    if (!line.trim()) {
      continue
    }

    // Regular paragraph
    elements.push(<p key={`p-${i}`}>{inlineFormat(line)}</p>)
  }

  flushList()
  if (inCodeBlock && codeLines.length) {
    elements.push(<pre key="code-end"><code>{codeLines.join('\n')}</code></pre>)
  }

  return elements
}

export default function ChatBubble({ role, content, timestamp, userName, index }: Props) {
  const [copied, setCopied] = useState(false)

  function handleCopy() {
    navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  const delay = Math.min(index * 30, 300)

  if (role === 'assistant') {
    return (
      <div
        className="flex gap-3 max-w-2xl animate-slideUp group"
        style={{ animationDelay: `${delay}ms` }}
      >
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-green-900 to-green-700 flex items-center justify-center shrink-0 mt-0.5 shadow-soft">
          <Bot size={14} color="white" />
        </div>
        <div className="relative bg-white rounded-2xl rounded-tl-md px-4 py-3 shadow-soft border border-gray-100/60 group-hover:shadow-card transition-shadow">
          <div className="chat-markdown text-sm text-gray-800 leading-relaxed">
            {renderMarkdown(content)}
          </div>
          <div className="flex items-center justify-between mt-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
            <span className="text-[10px] text-gray-300">{timestamp}</span>
            <button
              onClick={handleCopy}
              className="text-gray-300 hover:text-gray-500 transition-colors p-0.5"
              title="Copy message"
            >
              {copied ? <Check size={11} className="text-green-600" /> : <Copy size={11} />}
            </button>
          </div>
        </div>
      </div>
    )
  }

  // User bubble
  const initial = userName?.charAt(0)?.toUpperCase() || 'P'

  return (
    <div
      className="flex justify-end gap-2 items-end animate-slideUp"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="max-w-sm">
        <div className="bg-gradient-to-br from-green-900 to-green-800 text-white rounded-2xl rounded-br-md px-4 py-3 shadow-soft">
          <p className="text-sm leading-relaxed">{content}</p>
        </div>
        <p className="text-[10px] text-gray-300 text-right mt-1">
          {timestamp}
        </p>
      </div>
      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-gray-200 to-gray-300 flex items-center justify-center shrink-0">
        <span className="text-xs text-gray-600 font-semibold">{initial}</span>
      </div>
    </div>
  )
}
