import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import LoginPage from '../../pages/LoginPage'

const mockNavigate = vi.fn()

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => mockNavigate }
})

// Stub out LoginForm — its own tests cover form behaviour
vi.mock('../../components/LoginForm', () => ({
  default: ({ onSuccess }: { onSuccess: () => void }) => (
    <button data-testid="mock-login-form" onClick={onSuccess}>
      MockLoginForm
    </button>
  ),
}))

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  const renderPage = () =>
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    )

  // ─── Rendering ───────────────────────────────────────────────────────────────

  describe('rendering', () => {
    it('renders the "Sign in to your account" heading', () => {
      renderPage()
      expect(screen.getByRole('heading', { name: /sign in to your account/i })).toBeInTheDocument()
    })

    it('renders the LoginForm component', () => {
      renderPage()
      expect(screen.getByTestId('mock-login-form')).toBeInTheDocument()
    })

    it('renders a link to the register page', () => {
      renderPage()
      const link = screen.getByRole('link', { name: /register here/i })
      expect(link).toBeInTheDocument()
      expect(link).toHaveAttribute('href', '/register')
    })

    it('renders the background image', () => {
      renderPage()
      const img = screen.getByAltText('Background')
      expect(img).toBeInTheDocument()
    })
  })

  // ─── Navigation ──────────────────────────────────────────────────────────────

  describe('navigation', () => {
    it('navigates to /chat when LoginForm calls onSuccess', async () => {
      renderPage()
      await userEvent.click(screen.getByTestId('mock-login-form'))
      expect(mockNavigate).toHaveBeenCalledWith('/chat')
    })
  })
})
