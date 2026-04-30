import '@testing-library/jest-dom'
import { render, screen, fireEvent } from '@testing-library/react'
import BadgeSidebar from '@/components/BadgeSidebar'
import type { BadgeWithStatus } from '@/lib/types'

const mockBadge = (id: string, status: BadgeWithStatus['status'] = 'not_started'): BadgeWithStatus => ({
  id,
  title: `Badge ${id}`,
  type: 'Fundamentals',
  points: 15,
  pdf: `${id}.pdf`,
  status,
})

const defaultProps = {
  badgeGroups: {},
  selectedBadge: null,
  totalPoints: 0,
  conceptsUnlocked: false,
  advancedUnlocked: false,
  nextSuggestions: [],
  onSelectBadge: jest.fn(),
  onStatusChange: jest.fn(),
}

describe('BadgeSidebar', () => {
  beforeEach(() => jest.clearAllMocks())

  it('renders total points', () => {
    render(<BadgeSidebar {...defaultProps} totalPoints={42} />)
    expect(screen.getByText('42')).toBeInTheDocument()
  })

  it('shows Concepts unlocked badge when conceptsUnlocked is true', () => {
    render(<BadgeSidebar {...defaultProps} conceptsUnlocked={true} />)
    expect(screen.getByText(/Concepts ✓/)).toBeInTheDocument()
  })

  it('shows Concepts locked when conceptsUnlocked is false', () => {
    render(<BadgeSidebar {...defaultProps} conceptsUnlocked={false} />)
    expect(screen.getByText(/Concepts ○/)).toBeInTheDocument()
  })

  it('shows Advanced unlocked badge when advancedUnlocked is true', () => {
    render(<BadgeSidebar {...defaultProps} advancedUnlocked={true} />)
    expect(screen.getByText(/Advanced ✓/)).toBeInTheDocument()
  })

  it('renders badge names', () => {
    const props = {
      ...defaultProps,
      badgeGroups: { Fundamentals: [mockBadge('VSC1'), mockBadge('JCL1')] },
    }
    render(<BadgeSidebar {...props} />)
    expect(screen.getByText('Badge VSC1')).toBeInTheDocument()
    expect(screen.getByText('Badge JCL1')).toBeInTheDocument()
  })

  it('calls onSelectBadge when badge name is clicked', () => {
    const onSelectBadge = jest.fn()
    const props = {
      ...defaultProps,
      badgeGroups: { Fundamentals: [mockBadge('VSC1')] },
      onSelectBadge,
    }
    render(<BadgeSidebar {...props} />)
    fireEvent.click(screen.getByText('Badge VSC1'))
    expect(onSelectBadge).toHaveBeenCalledWith('VSC1')
  })

  it('calls onSelectBadge(null) when same badge is clicked again', () => {
    const onSelectBadge = jest.fn()
    const props = {
      ...defaultProps,
      badgeGroups: { Fundamentals: [mockBadge('VSC1')] },
      selectedBadge: 'VSC1',
      onSelectBadge,
    }
    render(<BadgeSidebar {...props} />)
    fireEvent.click(screen.getByText('Badge VSC1'))
    expect(onSelectBadge).toHaveBeenCalledWith(null)
  })

  it('cycles status when status icon is clicked', () => {
    const onStatusChange = jest.fn()
    const props = {
      ...defaultProps,
      badgeGroups: { Fundamentals: [mockBadge('VSC1', 'not_started')] },
      onStatusChange,
    }
    render(<BadgeSidebar {...props} />)
    const statusBtn = screen.getByTitle(/Status: not_started/)
    fireEvent.click(statusBtn)
    expect(onStatusChange).toHaveBeenCalledWith('VSC1', 'in_progress')
  })

  it('shows next suggestions when provided', () => {
    const props = { ...defaultProps, nextSuggestions: ['VSC1', 'JCL1'] }
    render(<BadgeSidebar {...props} />)
    expect(screen.getByText('VSC1')).toBeInTheDocument()
    expect(screen.getByText('JCL1')).toBeInTheDocument()
    expect(screen.getByText('Suggested next')).toBeInTheDocument()
  })

  it('shows legal disclaimer', () => {
    render(<BadgeSidebar {...defaultProps} />)
    expect(screen.getByText(/Unofficial tool for personal learning/i)).toBeInTheDocument()
    expect(screen.getByText(/IBM Corporation/i)).toBeInTheDocument()
  })

  it('shows progress bar percentage based on completed badges', () => {
    const props = {
      ...defaultProps,
      badgeGroups: {
        Fundamentals: [
          mockBadge('VSC1', 'completed'),
          mockBadge('JCL1', 'not_started'),
        ],
      },
    }
    render(<BadgeSidebar {...props} />)
    expect(screen.getByText('1/2 badges')).toBeInTheDocument()
  })
})
