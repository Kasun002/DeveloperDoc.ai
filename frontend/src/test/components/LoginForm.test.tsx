import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import LoginForm from '../../components/LoginForm'

vi.mock('../../services/authService')
vi.mock('../../utils/toast')

import { login, storeTokens } from '../../services/authService'
import { showSuccess, showError } from '../../utils/toast'

describe('LoginForm', () => {
  const onSuccess = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  // ─── Rendering ───────────────────────────────────────────────────────────────

  describe('rendering', () => {
    it('renders the email input', () => {
      render(<LoginForm onSuccess={onSuccess} />)
      expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    })

    it('renders the password input', () => {
      render(<LoginForm onSuccess={onSuccess} />)
      expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
    })

    it('renders the Log In submit button', () => {
      render(<LoginForm onSuccess={onSuccess} />)
      expect(screen.getByRole('button', { name: /log in/i })).toBeInTheDocument()
    })

    it('password input has type="password"', () => {
      render(<LoginForm onSuccess={onSuccess} />)
      expect(screen.getByLabelText(/password/i)).toHaveAttribute('type', 'password')
    })
  })

  // ─── Validation ──────────────────────────────────────────────────────────────

  describe('validation', () => {
    it('shows "Email is required" when email is empty on submit', async () => {
      render(<LoginForm onSuccess={onSuccess} />)
      await userEvent.click(screen.getByRole('button', { name: /log in/i }))
      expect(await screen.findByText('Email is required')).toBeInTheDocument()
    })

    it('shows "Please enter a valid email address" for invalid email format', async () => {
      render(<LoginForm onSuccess={onSuccess} />)
      await userEvent.type(screen.getByLabelText(/email/i), 'not-an-email')
      await userEvent.click(screen.getByRole('button', { name: /log in/i }))
      expect(await screen.findByText('Please enter a valid email address')).toBeInTheDocument()
    })

    it('shows "Password is required" when password is empty on submit', async () => {
      render(<LoginForm onSuccess={onSuccess} />)
      await userEvent.type(screen.getByLabelText(/email/i), 'user@test.com')
      await userEvent.click(screen.getByRole('button', { name: /log in/i }))
      expect(await screen.findByText('Password is required')).toBeInTheDocument()
    })

    it('does not call login when validation fails', async () => {
      render(<LoginForm onSuccess={onSuccess} />)
      await userEvent.click(screen.getByRole('button', { name: /log in/i }))
      await screen.findByText('Email is required')
      expect(login).not.toHaveBeenCalled()
    })
  })

  // ─── Successful submission ───────────────────────────────────────────────────

  describe('successful submission', () => {
    it('calls login with the submitted credentials', async () => {
      vi.mocked(login).mockResolvedValueOnce({
        access_token: 'at',
        refresh_token: 'rt',
        token_type: 'bearer',
      })

      render(<LoginForm onSuccess={onSuccess} />)
      await userEvent.type(screen.getByLabelText(/email/i), 'user@test.com')
      await userEvent.type(screen.getByLabelText(/password/i), 'mypassword')
      await userEvent.click(screen.getByRole('button', { name: /log in/i }))

      await waitFor(() =>
        expect(login).toHaveBeenCalledWith({ email: 'user@test.com', password: 'mypassword' })
      )
    })

    it('calls storeTokens with the returned tokens', async () => {
      const tokens = { access_token: 'at', refresh_token: 'rt', token_type: 'bearer' }
      vi.mocked(login).mockResolvedValueOnce(tokens)

      render(<LoginForm onSuccess={onSuccess} />)
      await userEvent.type(screen.getByLabelText(/email/i), 'user@test.com')
      await userEvent.type(screen.getByLabelText(/password/i), 'mypassword')
      await userEvent.click(screen.getByRole('button', { name: /log in/i }))

      await waitFor(() => expect(storeTokens).toHaveBeenCalledWith(tokens))
    })

    it('calls showSuccess with the welcome message', async () => {
      vi.mocked(login).mockResolvedValueOnce({
        access_token: 'at',
        refresh_token: 'rt',
        token_type: 'bearer',
      })

      render(<LoginForm onSuccess={onSuccess} />)
      await userEvent.type(screen.getByLabelText(/email/i), 'user@test.com')
      await userEvent.type(screen.getByLabelText(/password/i), 'mypassword')
      await userEvent.click(screen.getByRole('button', { name: /log in/i }))

      await waitFor(() =>
        expect(showSuccess).toHaveBeenCalledWith('Login successful! Welcome back.')
      )
    })

    it('calls onSuccess callback after successful login', async () => {
      vi.mocked(login).mockResolvedValueOnce({
        access_token: 'at',
        refresh_token: 'rt',
        token_type: 'bearer',
      })

      render(<LoginForm onSuccess={onSuccess} />)
      await userEvent.type(screen.getByLabelText(/email/i), 'user@test.com')
      await userEvent.type(screen.getByLabelText(/password/i), 'mypassword')
      await userEvent.click(screen.getByRole('button', { name: /log in/i }))

      await waitFor(() => expect(onSuccess).toHaveBeenCalled())
    })
  })

  // ─── Failed submission ───────────────────────────────────────────────────────

  describe('failed submission', () => {
    it('displays the error message in the form on login failure', async () => {
      vi.mocked(login).mockRejectedValueOnce(new Error('Invalid credentials. Please try again.'))

      render(<LoginForm onSuccess={onSuccess} />)
      await userEvent.type(screen.getByLabelText(/email/i), 'user@test.com')
      await userEvent.type(screen.getByLabelText(/password/i), 'wrongpassword')
      await userEvent.click(screen.getByRole('button', { name: /log in/i }))

      expect(await screen.findByText('Invalid credentials. Please try again.')).toBeInTheDocument()
    })

    it('calls showError with the error message on login failure', async () => {
      vi.mocked(login).mockRejectedValueOnce(new Error('Invalid credentials. Please try again.'))

      render(<LoginForm onSuccess={onSuccess} />)
      await userEvent.type(screen.getByLabelText(/email/i), 'user@test.com')
      await userEvent.type(screen.getByLabelText(/password/i), 'wrongpassword')
      await userEvent.click(screen.getByRole('button', { name: /log in/i }))

      await waitFor(() =>
        expect(showError).toHaveBeenCalledWith('Invalid credentials. Please try again.')
      )
    })

    it('does not call onSuccess when login fails', async () => {
      vi.mocked(login).mockRejectedValueOnce(new Error('Invalid credentials. Please try again.'))

      render(<LoginForm onSuccess={onSuccess} />)
      await userEvent.type(screen.getByLabelText(/email/i), 'user@test.com')
      await userEvent.type(screen.getByLabelText(/password/i), 'wrongpassword')
      await userEvent.click(screen.getByRole('button', { name: /log in/i }))

      await waitFor(() => expect(showError).toHaveBeenCalled())
      expect(onSuccess).not.toHaveBeenCalled()
    })
  })

  // ─── Submitting state ────────────────────────────────────────────────────────

  describe('submitting state', () => {
    it('shows "Logging in..." while the request is pending', async () => {
      vi.mocked(login).mockImplementation(() => new Promise(() => {}))

      render(<LoginForm onSuccess={onSuccess} />)
      await userEvent.type(screen.getByLabelText(/email/i), 'user@test.com')
      await userEvent.type(screen.getByLabelText(/password/i), 'mypassword')
      await userEvent.click(screen.getByRole('button', { name: /log in/i }))

      expect(await screen.findByText('Logging in...')).toBeInTheDocument()
    })

    it('disables inputs while submitting', async () => {
      vi.mocked(login).mockImplementation(() => new Promise(() => {}))

      render(<LoginForm onSuccess={onSuccess} />)
      await userEvent.type(screen.getByLabelText(/email/i), 'user@test.com')
      await userEvent.type(screen.getByLabelText(/password/i), 'mypassword')
      await userEvent.click(screen.getByRole('button', { name: /log in/i }))

      await screen.findByText('Logging in...')
      expect(screen.getByLabelText(/email/i)).toBeDisabled()
      expect(screen.getByLabelText(/password/i)).toBeDisabled()
    })
  })
})
