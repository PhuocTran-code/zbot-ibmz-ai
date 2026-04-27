'use client'

import { useState } from 'react'
import type { BadgeStatus, BadgeType, BadgeWithStatus } from '@/lib/types'

const TIER_ORDER: BadgeType[] = ['Fundamentals', 'Concepts', 'Advanced', 'AllStar']

const TIER_COLORS: Record<BadgeType, string> = {
  Fundamentals: 'bg-blue-600',
  Concepts: 'bg-purple-600',
  Advanced: 'bg-orange-500',
  AllStar: 'bg-yellow-500',
}

const TIER_TEXT: Record<BadgeType, string> = {
  Fundamentals: 'text-blue-400',
  Concepts: 'text-purple-400',
  Advanced: 'text-orange-400',
  AllStar: 'text-yellow-400',
}

const STATUS_ICONS: Record<BadgeStatus, string> = {
  not_started: '○',
  in_progress: '◑',
  completed: '●',
}

const STATUS_COLORS: Record<BadgeStatus, string> = {
  not_started: 'text-gray-500',
  in_progress: 'text-yellow-400',
  completed: 'text-green-400',
}

const STATUS_CYCLE: Record<BadgeStatus, BadgeStatus> = {
  not_started: 'in_progress',
  in_progress: 'completed',
  completed: 'not_started',
}

interface Props {
  badgeGroups: Record<string, BadgeWithStatus[]>
  selectedBadge: string | null
  totalPoints: number
  conceptsUnlocked: boolean
  advancedUnlocked: boolean
  nextSuggestions: string[]
  onSelectBadge: (id: string | null) => void
  onStatusChange: (badgeId: string, status: BadgeStatus) => void
}

export default function BadgeSidebar({
  badgeGroups,
  selectedBadge,
  totalPoints,
  conceptsUnlocked,
  advancedUnlocked,
  nextSuggestions,
  onSelectBadge,
  onStatusChange,
}: Props) {
  const [expandedTiers, setExpandedTiers] = useState<Set<string>>(
    new Set(TIER_ORDER),
  )

  function toggleTier(tier: string) {
    setExpandedTiers((prev) => {
      const next = new Set(prev)
      if (next.has(tier)) next.delete(tier)
      else next.add(tier)
      return next
    })
  }

  const totalBadges = Object.values(badgeGroups).flat().length
  const completedBadges = Object.values(badgeGroups)
    .flat()
    .filter((b) => b.status === 'completed').length

  return (
    <aside className="flex flex-col w-72 min-w-72 bg-gray-900 border-r border-gray-700 overflow-y-auto">
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
          IBM Z Xplore
        </h2>
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-bold text-white">{totalPoints}</span>
          <span className="text-gray-400 text-sm">pts</span>
        </div>
        <div className="mt-2">
          <div className="flex justify-between text-xs text-gray-500 mb-1">
            <span>{completedBadges}/{totalBadges} badges</span>
          </div>
          <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 rounded-full transition-all"
              style={{ width: `${totalBadges > 0 ? (completedBadges / totalBadges) * 100 : 0}%` }}
            />
          </div>
        </div>

        {/* Unlock badges */}
        <div className="mt-3 flex gap-2">
          <span
            className={`text-xs px-2 py-0.5 rounded-full font-medium ${
              conceptsUnlocked
                ? 'bg-purple-900 text-purple-300'
                : 'bg-gray-800 text-gray-500'
            }`}
          >
            Concepts {conceptsUnlocked ? '✓' : '○'}
          </span>
          <span
            className={`text-xs px-2 py-0.5 rounded-full font-medium ${
              advancedUnlocked
                ? 'bg-orange-900 text-orange-300'
                : 'bg-gray-800 text-gray-500'
            }`}
          >
            Advanced {advancedUnlocked ? '✓' : '○'}
          </span>
        </div>
      </div>

      {/* Next suggestions */}
      {nextSuggestions.length > 0 && (
        <div className="px-4 py-3 border-b border-gray-700 bg-blue-950/40">
          <p className="text-xs text-blue-400 font-medium mb-1">Suggested next</p>
          <div className="flex flex-wrap gap-1">
            {nextSuggestions.map((id) => (
              <button
                key={id}
                onClick={() => onSelectBadge(id === selectedBadge ? null : id)}
                className="text-xs bg-blue-800/50 text-blue-200 px-2 py-0.5 rounded hover:bg-blue-700/60 transition-colors"
              >
                {id}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* All badge button */}
      <div className="px-4 pt-3">
        <button
          onClick={() => onSelectBadge(null)}
          className={`w-full text-left text-xs px-3 py-2 rounded transition-colors ${
            selectedBadge === null
              ? 'bg-blue-700 text-white'
              : 'text-gray-400 hover:bg-gray-800'
          }`}
        >
          All badges (no filter)
        </button>
      </div>

      {/* Badge tiers */}
      <div className="flex-1 px-4 py-2">
        {TIER_ORDER.map((tier) => {
          const badges = badgeGroups[tier] ?? []
          if (badges.length === 0) return null
          const isExpanded = expandedTiers.has(tier)
          const tierCompleted = badges.filter((b) => b.status === 'completed').length

          return (
            <div key={tier} className="mb-3">
              <button
                onClick={() => toggleTier(tier)}
                className="w-full flex items-center justify-between py-1.5 text-left group"
              >
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${TIER_COLORS[tier]}`} />
                  <span className={`text-xs font-semibold ${TIER_TEXT[tier]}`}>
                    {tier}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-500">
                    {tierCompleted}/{badges.length}
                  </span>
                  <span className="text-gray-600 text-xs">{isExpanded ? '▲' : '▼'}</span>
                </div>
              </button>

              {isExpanded && (
                <div className="space-y-0.5 ml-1">
                  {badges.map((badge) => (
                    <div
                      key={badge.id}
                      className={`flex items-center gap-2 rounded px-2 py-1.5 cursor-pointer transition-colors group ${
                        selectedBadge === badge.id
                          ? 'bg-gray-700'
                          : 'hover:bg-gray-800'
                      }`}
                    >
                      {/* Status icon — click to cycle */}
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          onStatusChange(badge.id, STATUS_CYCLE[badge.status])
                        }}
                        className={`text-base leading-none flex-shrink-0 ${STATUS_COLORS[badge.status]} hover:scale-125 transition-transform`}
                        title={`Status: ${badge.status} (click to change)`}
                      >
                        {STATUS_ICONS[badge.status]}
                      </button>

                      {/* Badge name */}
                      <button
                        onClick={() =>
                          onSelectBadge(
                            badge.id === selectedBadge ? null : badge.id,
                          )
                        }
                        className="flex-1 text-left min-w-0"
                      >
                        <p
                          className={`text-xs truncate ${
                            badge.status === 'completed'
                              ? 'text-gray-400 line-through'
                              : 'text-gray-200'
                          }`}
                        >
                          {badge.title}
                        </p>
                        <p className="text-xs text-gray-600">{badge.id}</p>
                      </button>

                      {/* Points */}
                      <span className="text-xs text-gray-600 flex-shrink-0">
                        {badge.points}p
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Legend */}
      <div className="px-4 py-3 border-t border-gray-700 text-xs text-gray-600 space-y-0.5">
        <p>○ not started  ◑ in progress  ● completed</p>
        <p>Click badge name to filter chat.</p>
        <p>Click status icon to update.</p>
      </div>
    </aside>
  )
}
