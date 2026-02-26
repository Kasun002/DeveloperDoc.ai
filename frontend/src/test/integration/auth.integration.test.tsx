/**
 * Auth integration tests
 *
 * Real services + real components + MSW at the network level.
 * No vi.mock() for services or child components.
 */
import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { AppRouter } from '../../routes/AppRouter'
import { server } from './mocks/server'

// ─── MSW lifecycle ────────────────────────────────────────────────────────────

beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }))
afterEach(() => {
  server.resetHandlers()
  // Clear auth cookies between tests
  document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/'
  document.cookie = 'refresh_token=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/'
})
afterAll(() => server.close())

// ─── Helper ───────────────────────────────────────────────────────────────────

const renderAt = (route: string) =>
  render(
    <MemoryRouter initialEntries={[route]}>
      <AppRouter />
    </MemoryRouter>
  )

// ─── Login flow ───────────────────────────────────────────────────────────────

describe('Login flow', () => {
  it('renders the login page at /login', () => {
    renderAt('/login')
    expect(screen.getByRole('heading', { name: /sign in to your account/i })).toBeInTheDocument()
  })

  it('navigates to /chat after successful login', async () => {
    renderAt('/login')

    await userEvent.type(screen.getByLabelText(/email/i), 'test@example.com')
    await userEvent.type(screen.getByLabelText(/password/i), 'password123')
    await userEvent.click(screen.getByRole('button', { name: /log in/i }))

    // ChatPage header should appear after navigation
    await waitFor(() =>
      expect(screen.getByAltText('DeveloperDoc.ai Logo')).toBeInTheDocument()
    )
  })

  it('stores tokens in cookies after successful login', async () => {
    renderAt('/login')

    await userEvent.type(screen.getByLabelText(/email/i), 'test@example.com')
    await userEvent.type(screen.getByLabelText(/password/i), 'password123')
    await userEvent.click(screen.getByRole('button', { name: /log in/i }))

    await waitFor(() =>
      expect(document.cookie).toContain('access_token=valid-token')
    )
  })

  it('shows an error message on invalid credentials', async () => {
    renderAt('/login')

    await userEvent.type(screen.getByLabelText(/email/i), 'wrong@example.com')
    await userEvent.type(screen.getByLabelText(/password/i), 'wrongpassword')
    await userEvent.click(screen.getByRole('button', { name: /log in/i }))

    expect(
      await screen.findByText('Invalid credentials. Please try again.')
    ).toBeInTheDocument()
  })

  it('stays on the login page when credentials are wrong', async () => {
    renderAt('/login')

    await userEvent.type(screen.getByLabelText(/email/i), 'wrong@example.com')
    await userEvent.type(screen.getByLabelText(/password/i), 'wrongpassword')
    await userEvent.click(screen.getByRole('button', { name: /log in/i }))

    await screen.findByText('Invalid credentials. Please try again.')
    expect(screen.getByRole('heading', { name: /sign in to your account/i })).toBeInTheDocument()
  })

  it('renders a link to the register page from login', () => {
    renderAt('/login')
    expect(screen.getByRole('link', { name: /register here/i })).toBeInTheDocument()
  })
})

// ─── Register flow ────────────────────────────────────────────────────────────

describe('Register flow', () => {
  it('renders the register page at /register', () => {
    renderAt('/register')
    expect(screen.getByRole('heading', { name: /create your account/i })).toBeInTheDocument()
  })

  it('redirects to /login after successful registration', async () => {
    renderAt('/register')

    await userEvent.type(screen.getByLabelText(/email/i), 'newuser@example.com')
    await userEvent.type(screen.getByLabelText(/password/i), 'securepassword')
    await userEvent.click(screen.getByRole('button', { name: /^register$/i }))

    await waitFor(() =>
      expect(
        screen.getByRole('heading', { name: /sign in to your account/i })
      ).toBeInTheDocument()
    )
  })

  it('does not store tokens in cookies after registration', async () => {
    renderAt('/register')

    await userEvent.type(screen.getByLabelText(/email/i), 'newuser@example.com')
    await userEvent.type(screen.getByLabelText(/password/i), 'securepassword')
    await userEvent.click(screen.getByRole('button', { name: /^register$/i }))

    await waitFor(() =>
      screen.getByRole('heading', { name: /sign in to your account/i })
    )
    expect(document.cookie).not.toContain('access_token')
  })

  it('shows an error for an already-registered email', async () => {
    renderAt('/register')

    await userEvent.type(screen.getByLabelText(/email/i), 'existing@example.com')
    await userEvent.type(screen.getByLabelText(/password/i), 'somepassword')
    await userEvent.click(screen.getByRole('button', { name: /^register$/i }))

    expect(await screen.findByText('Email already registered')).toBeInTheDocument()
  })

  it('stays on the register page when registration fails', async () => {
    renderAt('/register')

    await userEvent.type(screen.getByLabelText(/email/i), 'existing@example.com')
    await userEvent.type(screen.getByLabelText(/password/i), 'somepassword')
    await userEvent.click(screen.getByRole('button', { name: /^register$/i }))

    await screen.findByText('Email already registered')
    expect(screen.getByRole('heading', { name: /create your account/i })).toBeInTheDocument()
  })

  it('renders a link back to the login page from register', () => {
    renderAt('/register')
    expect(screen.getByRole('link', { name: /sign in here/i })).toBeInTheDocument()
  })
})
