import type {
  Badge,
  BadgeStatus,
  BadgeWithStatus,
  ChatMessage,
  ProgressUpdateResult,
  UserProgress,
} from './types'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function fetchBadges(): Promise<Record<string, Badge[]>> {
  const res = await fetch(`${API_URL}/badges`)
  if (!res.ok) throw new Error('Failed to fetch badges')
  const data = await res.json()
  return data.badges
}

export async function sendChat(
  userId: string,
  message: string,
  badgeFilter: string | null,
): Promise<Omit<ChatMessage, 'id' | 'role'>> {
  const res = await fetch(`${API_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: userId,
      message,
      badge_filter: badgeFilter ?? undefined,
    }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? 'Chat request failed')
  }
  const data = await res.json()
  return {
    content: data.answer,
    sources: data.sources,
    provider: data.provider,
    suggestion: data.suggestion,
    follow_up_questions: data.follow_up_questions ?? [],
    error: data.error,
  }
}

export async function fetchProgress(userId: string): Promise<UserProgress> {
  const res = await fetch(`${API_URL}/progress/${encodeURIComponent(userId)}`)
  if (!res.ok) throw new Error('Failed to fetch progress')
  return res.json()
}

export async function updateBadgeStatus(
  userId: string,
  badgeId: string,
  status: BadgeStatus,
): Promise<ProgressUpdateResult> {
  const res = await fetch(`${API_URL}/progress`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, badge_id: badgeId, status }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? 'Progress update failed')
  }
  return res.json()
}

export function mergeBadgesWithProgress(
  badgeGroups: Record<string, Badge[]>,
  progressBadges: BadgeWithStatus[],
): Record<string, BadgeWithStatus[]> {
  const statusMap = new Map(progressBadges.map((b) => [b.id, b.status]))
  const result: Record<string, BadgeWithStatus[]> = {}
  for (const [type, badges] of Object.entries(badgeGroups)) {
    result[type] = badges.map((b) => ({
      ...b,
      status: statusMap.get(b.id) ?? 'not_started',
    }))
  }
  return result
}
