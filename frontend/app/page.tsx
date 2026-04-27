'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import BadgeSidebar from '@/components/BadgeSidebar'
import ChatPanel from '@/components/ChatPanel'
import {
  fetchBadges,
  fetchProgress,
  mergeBadgesWithProgress,
  sendChat,
  updateBadgeStatus,
} from '@/lib/api'
import type { BadgeStatus, BadgeWithStatus, ChatMessage, UserProgress } from '@/lib/types'

const USER_ID_KEY = 'zbot_user_id'
const TIER_ORDER = ['Fundamentals', 'Concepts', 'Advanced', 'AllStar']

function generateUserId(): string {
  return 'user_' + Math.random().toString(36).slice(2, 10)
}

function getUserId(): string {
  let id = localStorage.getItem(USER_ID_KEY)
  if (!id) {
    id = generateUserId()
    localStorage.setItem(USER_ID_KEY, id)
  }
  return id
}

export default function Home() {
  const [userId, setUserId] = useState<string>('guest')
  const [badgeGroups, setBadgeGroups] = useState<Record<string, BadgeWithStatus[]>>({})
  const [progress, setProgress] = useState<Omit<UserProgress, 'badges'>>({
    user_id: 'guest',
    total_points: 0,
    concepts_unlocked: false,
    advanced_unlocked: false,
    next_suggestions: [],
  })
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [selectedBadge, setSelectedBadge] = useState<string | null>(null)
  const msgIdCounter = useRef(0)

  function nextId() {
    msgIdCounter.current += 1
    return String(msgIdCounter.current)
  }

  // Initialize userId from localStorage on mount (client-side only)
  useEffect(() => {
    setUserId(getUserId())
  }, [])

  // Load badges + progress whenever userId is ready
  useEffect(() => {
    if (userId === 'guest') return
    async function load() {
      try {
        const [badgesData, progressData] = await Promise.all([
          fetchBadges(),
          fetchProgress(userId),
        ])
        const merged = mergeBadgesWithProgress(badgesData, progressData.badges)
        const ordered: Record<string, BadgeWithStatus[]> = {}
        for (const tier of TIER_ORDER) {
          if (merged[tier]) ordered[tier] = merged[tier]
        }
        setBadgeGroups(ordered)
        setProgress({
          user_id: progressData.user_id,
          total_points: progressData.total_points,
          concepts_unlocked: progressData.concepts_unlocked,
          advanced_unlocked: progressData.advanced_unlocked,
          next_suggestions: progressData.next_suggestions,
        })
      } catch (err) {
        console.error('Failed to load data:', err)
        // If backend not running, still load badges for display
        fetchBadges()
          .then((badgesData) => {
            const ordered: Record<string, BadgeWithStatus[]> = {}
            for (const tier of TIER_ORDER) {
              if (badgesData[tier]) {
                ordered[tier] = badgesData[tier].map((b) => ({
                  ...b,
                  status: 'not_started' as BadgeStatus,
                }))
              }
            }
            setBadgeGroups(ordered)
          })
          .catch(() => {})
      }
    }
    load()
  }, [userId])

  const selectedBadgeTitle = selectedBadge
    ? Object.values(badgeGroups)
        .flat()
        .find((b) => b.id === selectedBadge)?.title ?? null
    : null

  const handleSend = useCallback(
    async (text: string) => {
      const userMsg: ChatMessage = { id: nextId(), role: 'user', content: text }
      setMessages((prev) => [...prev, userMsg])
      setIsLoading(true)

      try {
        const result = await sendChat(userId, text, selectedBadge)
        const botMsg: ChatMessage = {
          id: nextId(),
          role: 'assistant',
          content: result.content,
          sources: result.sources,
          provider: result.provider,
          suggestion: result.suggestion,
          follow_up_questions: result.follow_up_questions,
          error: result.error,
        }
        setMessages((prev) => [...prev, botMsg])

        // Refresh suggestions
        const progressData = await fetchProgress(userId)
        setProgress((prev) => ({
          ...prev,
          total_points: progressData.total_points,
          concepts_unlocked: progressData.concepts_unlocked,
          advanced_unlocked: progressData.advanced_unlocked,
          next_suggestions: progressData.next_suggestions,
        }))
      } catch (err) {
        setMessages((prev) => [
          ...prev,
          {
            id: nextId(),
            role: 'assistant',
            content: 'Sorry, could not connect to ZBot. Make sure the backend is running on port 8000.',
            error: String(err),
          },
        ])
      } finally {
        setIsLoading(false)
      }
    },
    [userId, selectedBadge],
  )

  const handleStatusChange = useCallback(
    async (badgeId: string, status: BadgeStatus) => {
      // Optimistic update
      setBadgeGroups((prev) => {
        const next: Record<string, BadgeWithStatus[]> = {}
        for (const [tier, badges] of Object.entries(prev)) {
          next[tier] = badges.map((b) => (b.id === badgeId ? { ...b, status } : b))
        }
        return next
      })

      try {
        const result = await updateBadgeStatus(userId, badgeId, status)
        const progressData = await fetchProgress(userId)
        setProgress({
          user_id: userId,
          total_points: progressData.total_points,
          concepts_unlocked: result.concepts_unlocked,
          advanced_unlocked: result.advanced_unlocked,
          next_suggestions: progressData.next_suggestions,
        })
        // Sync badge list with latest server state
        setBadgeGroups((prev) => {
          const rawGroups = Object.fromEntries(
            Object.entries(prev).map(([k, v]) => [k, v.map(({ status: _s, ...b }) => b)]),
          )
          const merged = mergeBadgesWithProgress(rawGroups, progressData.badges)
          const ordered: Record<string, BadgeWithStatus[]> = {}
          for (const tier of TIER_ORDER) {
            if (merged[tier]) ordered[tier] = merged[tier]
          }
          return ordered
        })
      } catch (err) {
        console.error('Status update failed:', err)
      }
    },
    [userId],
  )

  return (
    <div className="flex h-screen overflow-hidden">
      <BadgeSidebar
        badgeGroups={badgeGroups}
        selectedBadge={selectedBadge}
        totalPoints={progress.total_points}
        conceptsUnlocked={progress.concepts_unlocked}
        advancedUnlocked={progress.advanced_unlocked}
        nextSuggestions={progress.next_suggestions}
        onSelectBadge={setSelectedBadge}
        onStatusChange={handleStatusChange}
      />
      <ChatPanel
        messages={messages}
        selectedBadge={selectedBadge}
        selectedBadgeTitle={selectedBadgeTitle}
        isLoading={isLoading}
        onSend={handleSend}
        onClearFilter={() => setSelectedBadge(null)}
      />
    </div>
  )
}
