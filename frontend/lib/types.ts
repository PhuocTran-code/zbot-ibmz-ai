export type BadgeStatus = 'not_started' | 'in_progress' | 'completed'
export type BadgeType = 'Fundamentals' | 'Concepts' | 'Advanced' | 'AllStar'

export interface Badge {
  id: string
  title: string
  type: BadgeType
  points: number
  pdf: string
}

export interface BadgeWithStatus extends Badge {
  status: BadgeStatus
}

export interface Source {
  badge_id: string
  badge_type: string
  step_number: number
  step_title: string
  points: number
  chunk_id: string
  score: number
  document: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
  provider?: string
  suggestion?: string[]
  follow_up_questions?: string[]
  error?: string | null
}

export interface UserProgress {
  user_id: string
  badges: BadgeWithStatus[]
  total_points: number
  concepts_unlocked: boolean
  advanced_unlocked: boolean
  next_suggestions: string[]
}

export interface ProgressUpdateResult {
  user_id: string
  badge_id: string
  status: BadgeStatus
  concepts_unlocked: boolean
  advanced_unlocked: boolean
}
