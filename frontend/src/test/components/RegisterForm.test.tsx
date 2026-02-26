import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import RegisterForm from '../../components/RegisterForm'

vi.mock('../../services/authService')
vi.mock('../../utils/toast')

import { register as registerUser, storeTokens } from '../../services/authService'
import { showSuccess, showError } from '../../utils/toast'

describe('RegisterForm', () => {
  const onSuccess = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  // ─── Rendering ───────────────────────────────────────────────────────────────

  describe('rendering', () => {
    it('renders the email input', () => {
      render(<RegisterForm onSuccess={onSuccess} />)
      expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    })

    it('renders the password input', () => {
      render(<RegisterForm onSuccess={onSuccess} />)
      expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
    })

    it('renders the Register submit button', () => {
      render(<RegisterForm onSuccess={onSuccess} />)
      expect(screen.getByRole('button', { name: /^register$/i })).toBeInTheDocument()
    })

    it('password input has type="password"', () => {
      render(<RegisterForm onSuccess={onSuccess} />)
      expect(screen.getByLabelText(/password/i)).toHaveAttribute('type', 'password')
    })
  })

  // ─── Validation ──────────────────────────────────────────────────────────────

  describe('validation', () => {
    it('shows "Email is required" when email is empty on submit', async () => {
      render(<RegisterForm onSuccess={onSuccess} />)
      await userEvent.click(screen.getByRole('button', { name: /^register$/i }))
      expect(await screen.findByText('Email is required')).toBeInTheDocument()
    })

    it('shows "Please enter a valid email address" for invalid email format', async () => {
      render(<RegisterForm onSuccess={onSuccess} />)
      await userEvent.type(screen.getByLabelText(/email/i), 'bad-email')
      await userEvent.click(screen.getByRole('button', { name: /^register$/i }))
      expect(await screen.findByText('Please enter a valid email address')).toBeInTheDocument()
    })

    it('shows "Password is required" when password is empty', async () => {
      render(<RegisterForm onSuccess={onSuccess} />)
      await userEvent.type(screen.getByLabelText(/email/i), 'user@test.com')
      await userEvent.click(screen.getByRole('button', { name: /^register$/i }))
      expect(await screen.findByText('Password is required')).toBeInTheDocument()
    })

    it('shows "Password must be at least 6 characters" for short passwords', async () => {
      render(<RegisterForm onSuccess={onSuccess} />)
      await userEvent.type(screen.getByLabelText(/email/i), 'user@test.com')
      await userEvent.type(screen.getByLabelText(/password/i), 'abc')
      await userEvent.click(screen.getByRole('button', { name: /^register$/i }))
      expect(await screen.findByText('Password must be at least 6 characters')).toBeInTheDocument()
    })

    it('does not call register when validation fails', async () => {
      render(<RegisterForm onSuccess={onSuccess} />)
      await userEvent.click(screen.getByRole('button', { name: /^register$/i }))
      await screen.findByText('Email is required')
      expect(registerUser).not.toHaveBeenCalled()
    })
  })

  // ─── Successful submission ───────────────────────────────────────────────────

  describe('successful submission', () => {
    it('calls register with the submitted credentials', async () => {
      vi.mocked(registerUser).mockResolvedValueOnce({
        access_token: 'at',
        refresh_token: 'rt',
        token_type: 'bearer',
      })

      render(<RegisterForm onSuccess={onSuccess} />)
      await userEvent.type(screen.getByLabelText(/email/i), 'new@test.com')
      await userEvent.type(screen.getByLabelText(/password/i), 'mypassword')
      await userEvent.click(screen.getByRole('button', { name: /^register$/i }))

      await waitFor(() =>
        expect(registerUser).toHaveBeenCalledWith({ email: 'new@test.com', password: 'mypassword' })
      )
    })

    it('calls storeTokens with the returned tokens', async () => {
      const tokens = { access_token: 'at', refresh_token: 'rt', token_type: 'bearer' }
      vi.mocked(registerUser).mockResolvedValueOnce(tokens)

      render(<RegisterForm onSuccess={onSuccess} />)
      await userEvent.type(screen.getByLabelText(/email/i), 'new@test.com')
      await userEvent.type(screen.getByLabelText(/password/i), 'mypassword')
      await userEvent.click(screen.getByRole('button', { name: /^register$/i }))

      await waitFor(() => expect(storeTokens).toHaveBeenCalledWith(tokens))
    })

    it('calls showSuccess with the welcome message', async () => {
      vi.mocked(registerUser).mockResolvedValueOnce({
        access_token: 'at',
        refresh_token: 'rt',
        token_type: 'bearer',
      })

      render(<RegisterForm onSuccess={onSuccess} />)
      await userEvent.type(screen.getByLabelText(/email/i), 'new@test.com')
      await userEvent.type(screen.getByLabelText(/password/i), 'mypassword')
      await userEvent.click(screen.getByRole('button', { name: /^register$/i }))

      await waitFor(() =>
        expect(showSuccess).toHaveBeenCalledWith(
          'Registration successful! Welcome to DeveloperDoc.ai'
        )
      )
    })

    it('calls onSuccess callback after successful registration', async () => {
      vi.mocked(registerUser).mockResolvedValueOnce({
        access_token: 'at',
        refresh_token: 'rt',
        token_type: 'bearer',
      })

      render(<RegisterForm onSuccess={onSuccess} />)
      await userEvent.type(screen.getByLabelText(/email/i), 'new@test.com')
      await userEvent.type(screen.getByLabelText(/password/i), 'mypassword')
      await userEvent.click(screen.getByRole('button', { name: /^register$/i }))

      await waitFor(() => expect(onSuccess).toHaveBeenCalled())
    })
  })

  // ─── Failed submission ───────────────────────────────────────────────────────

  describe('failed submission', () => {
    it('displays the error message in the form on register failure', async () => {
      vi.mocked(registerUser).mockRejectedValueOnce(new Error('Email already registered'))

      render(<RegisterForm onSuccess={onSuccess} />)
      await userEvent.type(screen.getByLabelText(/email/i), 'existing@test.com')
      await userEvent.type(screen.getByLabelText(/password/i), 'mypassword')
      await userEvent.click(screen.getByRole('button', { name: /^register$/i }))

      expect(await screen.findByText('Email already registered')).toBeInTheDocument()
    })

    it('calls showError with the error message on register failure', async () => {
      vi.mocked(registerUser).mockRejectedValueOnce(new Error('Email already registered'))

      render(<RegisterForm onSuccess={onSuccess} />)
      await userEvent.type(screen.getByLabelText(/email/i), 'existing@test.com')
      await userEvent.type(screen.getByLabelText(/password/i), 'mypassword')
      await userEvent.click(screen.getByRole('button', { name: /^register$/i }))

      await waitFor(() => expect(showError).toHaveBeenCalledWith('Email already registered'))
    })

    it('does not call onSuccess when registration fails', async () => {
      vi.mocked(registerUser).mockRejectedValueOnce(new Error('Email already registered'))

      render(<RegisterForm onSuccess={onSuccess} />)
      await userEvent.type(screen.getByLabelText(/email/i), 'existing@test.com')
      await userEvent.type(screen.getByLabelText(/password/i), 'mypassword')
      await userEvent.click(screen.getByRole('button', { name: /^register$/i }))

      await waitFor(() => expect(showError).toHaveBeenCalled())
      expect(onSuccess).not.toHaveBeenCalled()
    })
  })

  // ─── Submitting state ────────────────────────────────────────────────────────

  describe('submitting state', () => {
    it('shows "Registering..." while the request is pending', async () => {
      vi.mocked(registerUser).mockImplementation(() => new Promise(() => {}))

      render(<RegisterForm onSuccess={onSuccess} />)
      await userEvent.type(screen.getByLabelText(/email/i), 'new@test.com')
      await userEvent.type(screen.getByLabelText(/password/i), 'mypassword')
      await userEvent.click(screen.getByRole('button', { name: /^register$/i }))

      expect(await screen.findByText('Registering...')).toBeInTheDocument()
    })

    it('disables inputs while submitting', async () => {
      vi.mocked(registerUser).mockImplementation(() => new Promise(() => {}))

      render(<RegisterForm onSuccess={onSuccess} />)
      await userEvent.type(screen.getByLabelText(/email/i), 'new@test.com')
      await userEvent.type(screen.getByLabelText(/password/i), 'mypassword')
      await userEvent.click(screen.getByRole('button', { name: /^register$/i }))

      await screen.findByText('Registering...')
      expect(screen.getByLabelText(/email/i)).toBeDisabled()
      expect(screen.getByLabelText(/password/i)).toBeDisabled()
    })
  })
})
