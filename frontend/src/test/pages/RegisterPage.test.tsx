import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import RegisterPage from '../../pages/RegisterPage'

const mockNavigate = vi.fn()

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => mockNavigate }
})

// Stub out RegisterForm — its own tests cover form behaviour
vi.mock('../../components/RegisterForm', () => ({
  default: ({ onSuccess }: { onSuccess: () => void }) => (
    <button data-testid="mock-register-form" onClick={onSuccess}>
      MockRegisterForm
    </button>
  ),
}))

describe('RegisterPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  const renderPage = () =>
    render(
      <MemoryRouter>
        <RegisterPage />
      </MemoryRouter>
    )

  // ─── Rendering ───────────────────────────────────────────────────────────────

  describe('rendering', () => {
    it('renders the "Create your account" heading', () => {
      renderPage()
      expect(screen.getByRole('heading', { name: /create your account/i })).toBeInTheDocument()
    })

    it('renders the RegisterForm component', () => {
      renderPage()
      expect(screen.getByTestId('mock-register-form')).toBeInTheDocument()
    })

    it('renders a link back to the login page', () => {
      renderPage()
      const link = screen.getByRole('link', { name: /sign in here/i })
      expect(link).toBeInTheDocument()
      expect(link).toHaveAttribute('href', '/login')
    })

    it('renders the background image', () => {
      renderPage()
      const img = screen.getByAltText('Background')
      expect(img).toBeInTheDocument()
    })
  })

  // ─── Navigation ──────────────────────────────────────────────────────────────

  describe('navigation', () => {
    it('navigates to /login when RegisterForm calls onSuccess', async () => {
      renderPage()
      await userEvent.click(screen.getByTestId('mock-register-form'))
      expect(mockNavigate).toHaveBeenCalledWith('/login')
    })
  })
})
