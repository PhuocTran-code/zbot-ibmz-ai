import { mergeBadgesWithProgress } from '@/lib/api'
import type { Badge, BadgeWithStatus } from '@/lib/types'

const badge = (id: string): Badge => ({
  id,
  title: `Badge ${id}`,
  type: 'Fundamentals',
  points: 15,
  pdf: `${id}.pdf`,
})

describe('mergeBadgesWithProgress', () => {
  it('marks all badges as not_started when progress is empty', () => {
    const groups = { Fundamentals: [badge('VSC1'), badge('JCL1')] }
    const result = mergeBadgesWithProgress(groups, [])
    expect(result.Fundamentals.every((b) => b.status === 'not_started')).toBe(true)
  })

  it('applies the correct status from progress list', () => {
    const groups = { Fundamentals: [badge('VSC1')] }
    const progress: BadgeWithStatus[] = [
      { ...badge('VSC1'), status: 'completed' },
    ]
    const result = mergeBadgesWithProgress(groups, progress)
    expect(result.Fundamentals[0].status).toBe('completed')
  })

  it('defaults to not_started for badges not in progress list', () => {
    const groups = { Fundamentals: [badge('VSC1'), badge('JCL1')] }
    const progress: BadgeWithStatus[] = [{ ...badge('VSC1'), status: 'in_progress' }]
    const result = mergeBadgesWithProgress(groups, progress)
    expect(result.Fundamentals[0].status).toBe('in_progress')
    expect(result.Fundamentals[1].status).toBe('not_started')
  })

  it('preserves all badge groups and their order', () => {
    const groups = {
      Fundamentals: [badge('VSC1')],
      Advanced: [badge('ZCLI1')],
    }
    const result = mergeBadgesWithProgress(groups, [])
    expect(Object.keys(result)).toEqual(['Fundamentals', 'Advanced'])
    expect(result.Fundamentals).toHaveLength(1)
    expect(result.Advanced).toHaveLength(1)
  })

  it('does not mutate the input badge groups', () => {
    const groups = { Fundamentals: [badge('VSC1')] }
    const original = JSON.stringify(groups)
    mergeBadgesWithProgress(groups, [{ ...badge('VSC1'), status: 'completed' }])
    expect(JSON.stringify(groups)).toBe(original)
  })

  it('handles multiple groups and partial progress correctly', () => {
    const groups = {
      Fundamentals: [badge('VSC1'), badge('JCL1')],
      Concepts: [badge('CONCEPTS1')],
    }
    const progress: BadgeWithStatus[] = [
      { ...badge('JCL1'), status: 'completed' },
      { ...badge('CONCEPTS1'), status: 'in_progress' },
    ]
    const result = mergeBadgesWithProgress(groups, progress)
    expect(result.Fundamentals[0].status).toBe('not_started')
    expect(result.Fundamentals[1].status).toBe('completed')
    expect(result.Concepts[0].status).toBe('in_progress')
  })
})
