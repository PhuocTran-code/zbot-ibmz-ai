'use client'

import { useEffect, useRef, useState } from 'react'
import type { ChatMessage, Source } from '@/lib/types'

interface Props {
  messages: ChatMessage[]
  selectedBadge: string | null
  selectedBadgeTitle: string | null
  isLoading: boolean
  onSend: (message: string) => void
  onClearFilter: () => void
}

export default function ChatPanel({
  messages,
  selectedBadge,
  selectedBadgeTitle,
  isLoading,
  onSend,
  onClearFilter,
}: Props) {
  // onSend is reused as the follow-up handler — clicking a question sends it directly
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const text = input.trim()
    if (!text || isLoading) return
    onSend(text)
    setInput('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e as unknown as React.FormEvent)
    }
  }

  function handleInputChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setInput(e.target.value)
    const el = e.target
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 160) + 'px'
  }

  return (
    <div className="flex flex-col flex-1 min-w-0 bg-gray-950">
      {/* Top bar */}
      <div className="flex items-center gap-3 px-6 py-3 border-b border-gray-800 bg-gray-900">
        <div className="flex-1">
          <h1 className="text-base font-semibold text-white">ZBot</h1>
          <p className="text-xs text-gray-500">IBM Z Xplore AI Assistant</p>
        </div>
        {selectedBadge && (
          <div className="flex items-center gap-2 bg-blue-900/50 border border-blue-700 rounded-lg px-3 py-1.5">
            <span className="text-xs text-blue-300">
              Filtering: <span className="font-semibold">{selectedBadgeTitle ?? selectedBadge}</span>
            </span>
            <button
              onClick={onClearFilter}
              className="text-blue-500 hover:text-blue-300 text-sm leading-none"
              title="Remove filter"
            >
              ×
            </button>
          </div>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="text-4xl mb-4">🤖</div>
            <h2 className="text-xl font-semibold text-white mb-2">
              Hello! I&apos;m ZBot
            </h2>
            <p className="text-gray-400 text-sm max-w-md">
              I can help you learn IBM Z Xplore. Ask me anything about
              badges, JCL commands, USS, REXX, and more.
            </p>
            <div className="mt-6 grid grid-cols-2 gap-2 max-w-md">
              {[
                'What is JCL and how do I use it?',
                'How do I complete the VSC1 badge?',
                'Intro to Unix System Services',
                'Which badge should I study next?',
              ].map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => onSend(prompt)}
                  className="text-xs text-left bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg p-3 text-gray-300 transition-colors"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} onFollowUp={onSend} />
        ))}

        {isLoading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-blue-700 flex items-center justify-center text-sm flex-shrink-0">
              Z
            </div>
            <div className="bg-gray-800 rounded-2xl rounded-tl-sm px-4 py-3">
              <div className="flex gap-1 items-center h-5">
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0ms]" />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:150ms]" />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-6 py-4 border-t border-gray-800 bg-gray-900">
        <form onSubmit={handleSubmit} className="flex gap-3 items-end">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder={
              selectedBadge
                ? `Ask about ${selectedBadgeTitle ?? selectedBadge}…`
                : 'Ask ZBot anything about IBM Z…'
            }
            rows={1}
            className="flex-1 bg-gray-800 text-white placeholder-gray-500 border border-gray-700 rounded-xl px-4 py-3 text-sm resize-none focus:outline-none focus:border-blue-500 transition-colors"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 text-white px-4 py-3 rounded-xl text-sm font-medium transition-colors flex-shrink-0"
          >
            Send
          </button>
        </form>
        <p className="text-xs text-gray-600 mt-2 text-center">
          Enter to send · Shift+Enter for new line
        </p>
        <p className="text-xs text-gray-700 mt-1.5 text-center">
          Unofficial tool for personal learning · All IBM Z Xplore content © IBM Corporation
        </p>
      </div>
    </div>
  )
}

interface MessageBubbleProps {
  message: ChatMessage
  onFollowUp: (question: string) => void
}

function MessageBubble({ message, onFollowUp }: MessageBubbleProps) {
  const [showSources, setShowSources] = useState(false)
  const isUser = message.role === 'user'
  const hasFollowUp = !isUser && message.follow_up_questions && message.follow_up_questions.length > 0

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center text-sm flex-shrink-0 ${
          isUser ? 'bg-gray-600' : 'bg-blue-700'
        }`}
      >
        {isUser ? 'U' : 'Z'}
      </div>

      <div className={`flex flex-col gap-1 max-w-[75%] ${isUser ? 'items-end' : 'items-start'}`}>
        {/* Bubble */}
        <div
          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
            isUser
              ? 'bg-blue-600 text-white rounded-tr-sm'
              : 'bg-gray-800 text-gray-100 rounded-tl-sm'
          }`}
        >
          {message.content}
        </div>

        {/* Error */}
        {message.error && (
          <p className="text-xs text-red-400 px-1">⚠ {message.error}</p>
        )}

        {/* Meta: provider + sources toggle */}
        {!isUser && (
          <div className="flex items-center gap-3 px-1">
            {message.provider && (
              <span className="text-xs text-gray-600">{message.provider}</span>
            )}
            {message.sources && message.sources.length > 0 && (
              <button
                onClick={() => setShowSources((v) => !v)}
                className="text-xs text-blue-500 hover:text-blue-400 transition-colors"
              >
                {showSources ? 'Hide sources' : `${message.sources.length} source${message.sources.length !== 1 ? 's' : ''}`}
              </button>
            )}
            {message.suggestion && message.suggestion.length > 0 && (
              <span className="text-xs text-gray-600">
                Suggested: {message.suggestion.join(', ')}
              </span>
            )}
          </div>
        )}

        {/* Sources */}
        {showSources && message.sources && (
          <div className="mt-1 space-y-1 w-full">
            {message.sources.map((src) => (
              <SourceCard key={src.chunk_id} source={src} />
            ))}
          </div>
        )}

        {/* Follow-up questions */}
        {hasFollowUp && (
          <div className="mt-2 w-full">
            <p className="text-xs text-gray-500 mb-1.5 px-0.5">Explore deeper:</p>
            <div className="flex flex-col gap-1.5">
              {message.follow_up_questions!.map((q, i) => (
                <button
                  key={i}
                  onClick={() => onFollowUp(q)}
                  className="text-left text-xs bg-gray-800/80 hover:bg-gray-700 border border-gray-700 hover:border-blue-600 text-gray-300 hover:text-white rounded-lg px-3 py-2 transition-all duration-150 flex items-start gap-2 group"
                >
                  <span className="text-blue-500 group-hover:text-blue-400 mt-0.5 flex-shrink-0">▷</span>
                  <span>{q}</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function SourceCard({ source }: { source: Source }) {
  const [expanded, setExpanded] = useState(false)
  return (
    <div className="bg-gray-800/60 border border-gray-700 rounded-lg p-2 text-xs">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-gray-400">
          <span className="font-mono text-blue-400">{source.badge_id}</span>
          <span>
            {source.step_number === 0
              ? 'Overview'
              : `Step ${source.step_number} – ${source.step_title}`}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-gray-600">{(source.score * 100).toFixed(0)}%</span>
          <button
            onClick={() => setExpanded((v) => !v)}
            className="text-gray-500 hover:text-gray-300"
          >
            {expanded ? '▲' : '▼'}
          </button>
        </div>
      </div>
      {expanded && (
        <p className="mt-2 text-gray-400 leading-relaxed line-clamp-6">
          {source.document}
        </p>
      )}
    </div>
  )
}
