import '@testing-library/jest-dom'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ChatPanel from '@/components/ChatPanel'
import type { ChatMessage } from '@/lib/types'

const defaultProps = {
  messages: [],
  selectedBadge: null,
  selectedBadgeTitle: null,
  isLoading: false,
  onSend: jest.fn(),
  onClearFilter: jest.fn(),
}

const userMsg = (content: string): ChatMessage => ({
  id: '1',
  role: 'user',
  content,
})

const botMsg = (content: string, extras: Partial<ChatMessage> = {}): ChatMessage => ({
  id: '2',
  role: 'assistant',
  content,
  provider: 'gemini',
  sources: [],
  suggestion: [],
  follow_up_questions: [],
  ...extras,
})

describe('ChatPanel', () => {
  beforeEach(() => jest.clearAllMocks())

  it('renders ZBot header', () => {
    render(<ChatPanel {...defaultProps} />)
    expect(screen.getByText('ZBot')).toBeInTheDocument()
    expect(screen.getByText('IBM Z Xplore AI Assistant')).toBeInTheDocument()
  })

  it('shows welcome state when there are no messages', () => {
    render(<ChatPanel {...defaultProps} />)
    expect(screen.getByText(/Hello! I'm ZBot/)).toBeInTheDocument()
  })

  it('shows suggested prompt buttons in welcome state', () => {
    render(<ChatPanel {...defaultProps} />)
    expect(screen.getByText('What is JCL and how do I use it?')).toBeInTheDocument()
    expect(screen.getByText('How do I complete the VSC1 badge?')).toBeInTheDocument()
  })

  it('calls onSend when a suggested prompt is clicked', () => {
    const onSend = jest.fn()
    render(<ChatPanel {...defaultProps} onSend={onSend} />)
    fireEvent.click(screen.getByText('What is JCL and how do I use it?'))
    expect(onSend).toHaveBeenCalledWith('What is JCL and how do I use it?')
  })

  it('calls onSend when form is submitted with text', async () => {
    const onSend = jest.fn()
    const user = userEvent.setup()
    render(<ChatPanel {...defaultProps} onSend={onSend} />)
    const textarea = screen.getByPlaceholderText(/Ask ZBot anything/)
    await user.type(textarea, 'What is JCL?')
    await user.keyboard('{Enter}')
    expect(onSend).toHaveBeenCalledWith('What is JCL?')
  })

  it('does not call onSend when input is whitespace only', async () => {
    const onSend = jest.fn()
    const user = userEvent.setup()
    render(<ChatPanel {...defaultProps} onSend={onSend} />)
    const textarea = screen.getByPlaceholderText(/Ask ZBot anything/)
    await user.type(textarea, '   ')
    await user.keyboard('{Enter}')
    expect(onSend).not.toHaveBeenCalled()
  })

  it('send button is disabled when input is empty', () => {
    render(<ChatPanel {...defaultProps} />)
    expect(screen.getByRole('button', { name: /send/i })).toBeDisabled()
  })

  it('send button is disabled while loading', async () => {
    const user = userEvent.setup()
    render(<ChatPanel {...defaultProps} isLoading={true} />)
    const textarea = screen.getByRole('textbox')
    await user.type(textarea, 'Hello')
    expect(screen.getByRole('button', { name: /send/i })).toBeDisabled()
  })

  it('renders user messages', () => {
    render(<ChatPanel {...defaultProps} messages={[userMsg('Hello ZBot')]} />)
    expect(screen.getByText('Hello ZBot')).toBeInTheDocument()
  })

  it('renders assistant messages', () => {
    render(<ChatPanel {...defaultProps} messages={[botMsg('JCL stands for Job Control Language.')]} />)
    expect(screen.getByText('JCL stands for Job Control Language.')).toBeInTheDocument()
  })

  it('shows provider name on assistant messages', () => {
    render(<ChatPanel {...defaultProps} messages={[botMsg('Answer', { provider: 'groq' })]} />)
    expect(screen.getByText('groq')).toBeInTheDocument()
  })

  it('shows follow-up questions as clickable buttons', () => {
    const msg = botMsg('Answer', { follow_up_questions: ['What is JES2?', 'How does EBCDIC work?'] })
    render(<ChatPanel {...defaultProps} messages={[msg]} />)
    expect(screen.getByText('What is JES2?')).toBeInTheDocument()
    expect(screen.getByText('How does EBCDIC work?')).toBeInTheDocument()
  })

  it('calls onSend when follow-up question is clicked', () => {
    const onSend = jest.fn()
    const msg = botMsg('Answer', { follow_up_questions: ['What is JES2?'] })
    render(<ChatPanel {...defaultProps} messages={[msg]} onSend={onSend} />)
    fireEvent.click(screen.getByText('What is JES2?'))
    expect(onSend).toHaveBeenCalledWith('What is JES2?')
  })

  it('shows badge filter chip when a badge is selected', () => {
    render(
      <ChatPanel
        {...defaultProps}
        selectedBadge="VSC1"
        selectedBadgeTitle="Visual Studio Code"
      />,
    )
    expect(screen.getByText(/Visual Studio Code/)).toBeInTheDocument()
    expect(screen.getByTitle('Remove filter')).toBeInTheDocument()
  })

  it('calls onClearFilter when filter × is clicked', () => {
    const onClearFilter = jest.fn()
    render(
      <ChatPanel
        {...defaultProps}
        selectedBadge="VSC1"
        selectedBadgeTitle="Visual Studio Code"
        onClearFilter={onClearFilter}
      />,
    )
    fireEvent.click(screen.getByTitle('Remove filter'))
    expect(onClearFilter).toHaveBeenCalled()
  })

  it('shows legal disclaimer', () => {
    render(<ChatPanel {...defaultProps} />)
    expect(screen.getByText(/Unofficial tool for personal learning/i)).toBeInTheDocument()
    expect(screen.getByText(/IBM Corporation/i)).toBeInTheDocument()
  })

  it('shows sources toggle when sources exist', () => {
    const msg = botMsg('Answer', {
      sources: [{
        badge_id: 'VSC1', badge_type: 'Fundamentals', step_number: 1,
        step_title: 'CONNECT', points: 15, chunk_id: 'VSC1_step_1',
        score: 0.87, document: 'Connect to Z...',
      }],
    })
    render(<ChatPanel {...defaultProps} messages={[msg]} />)
    expect(screen.getByText('1 source')).toBeInTheDocument()
  })
})
