import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { ChatPage } from '../../pages/ChatPage'

const mockNavigate = vi.fn()

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => mockNavigate }
})

vi.mock('../../services/authService')

// Stub ChatInterface — its own tests cover chat behaviour
vi.mock('../../components/ChatInterface', () => ({
  default: () => <div data-testid="mock-chat-interface" />,
}))

import { clearTokens } from '../../services/authService'

describe('ChatPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  const renderPage = () =>
    render(
      <MemoryRouter>
        <ChatPage />
      </MemoryRouter>
    )

  // ─── Rendering ───────────────────────────────────────────────────────────────

  describe('rendering', () => {
    it('renders the logo image', () => {
      renderPage()
      expect(screen.getByAltText('DeveloperDoc.ai Logo')).toBeInTheDocument()
    })

    it('renders the Logout button', () => {
      renderPage()
      expect(screen.getByRole('button', { name: /logout/i })).toBeInTheDocument()
    })

    it('renders the ChatInterface component', () => {
      renderPage()
      expect(screen.getByTestId('mock-chat-interface')).toBeInTheDocument()
    })
  })

  // ─── Logout ───────────────────────────────────────────────────────────────────

  describe('logout', () => {
    it('calls clearTokens when Logout is clicked', async () => {
      renderPage()
      await userEvent.click(screen.getByRole('button', { name: /logout/i }))
      expect(clearTokens).toHaveBeenCalled()
    })

    it('navigates to /login with replace after logout', async () => {
      renderPage()
      await userEvent.click(screen.getByRole('button', { name: /logout/i }))
      expect(mockNavigate).toHaveBeenCalledWith('/login', { replace: true })
    })
  })
})
