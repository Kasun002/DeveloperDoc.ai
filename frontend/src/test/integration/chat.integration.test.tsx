/**
 * Chat integration tests
 *
 * Real services + real components + MSW at the network level.
 * Requires a valid access_token cookie to pass ProtectedRoute.
 */
import { describe, it, expect, beforeAll, beforeEach, afterAll, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { AppRouter } from '../../routes/AppRouter'
import { server } from './mocks/server'

// ─── MSW lifecycle ────────────────────────────────────────────────────────────

beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }))
afterEach(() => {
  server.resetHandlers()
  document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/'
  document.cookie = 'refresh_token=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/'
})
afterAll(() => server.close())

// ─── Helpers ──────────────────────────────────────────────────────────────────

const setValidToken = () => {
  document.cookie = 'access_token=valid-token; path=/'
}

const setExpiredToken = () => {
  document.cookie = 'access_token=expired-token; path=/'
}

const renderChat = () =>
  render(
    <MemoryRouter initialEntries={['/chat']}>
      <AppRouter />
    </MemoryRouter>
  )

// ─── Chat page rendering ──────────────────────────────────────────────────────

describe('Chat page rendering', () => {
  beforeEach(setValidToken)

  it('renders the chat page when a valid token is present', () => {
    renderChat()
    expect(screen.getByAltText('DeveloperDoc.ai Logo')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /logout/i })).toBeInTheDocument()
  })

  it('renders the prompt input and Send button', () => {
    renderChat()
    expect(screen.getByPlaceholderText('Ask me anything...')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /send/i })).toBeInTheDocument()
  })

  it('shows the empty state message before any query', () => {
    renderChat()
    expect(screen.getByText('Ask a question to get started')).toBeInTheDocument()
  })
})

// ─── Query submission ─────────────────────────────────────────────────────────

describe('Query submission', () => {
  beforeEach(setValidToken)

  it('displays the API response as rendered markdown after a query', async () => {
    renderChat()

    await userEvent.type(screen.getByPlaceholderText('Ask me anything...'), 'What is React?')
    await userEvent.click(screen.getByRole('button', { name: /send/i }))

    // MSW returns "## Result\n\nThis is the answer to: **What is React?**"
    // MarkdownRenderer turns the heading into an h2
    await waitFor(() =>
      expect(screen.getByRole('heading', { level: 2, name: /result/i })).toBeInTheDocument()
    )
  })

  it('renders bold text from the markdown response', async () => {
    renderChat()

    await userEvent.type(screen.getByPlaceholderText('Ask me anything...'), 'What is React?')
    await userEvent.click(screen.getByRole('button', { name: /send/i }))

    await waitFor(() => {
      const strong = document.querySelector('strong')
      expect(strong).toBeInTheDocument()
      expect(strong).toHaveTextContent('What is React?')
    })
  })

  it('clears the input field after a successful query', async () => {
    renderChat()
    const input = screen.getByPlaceholderText('Ask me anything...')

    await userEvent.type(input, 'What is React?')
    await userEvent.click(screen.getByRole('button', { name: /send/i }))

    await waitFor(() => expect(input).toHaveValue(''))
  })
})

// ─── Session expiry ───────────────────────────────────────────────────────────

describe('Session expiry', () => {
  beforeEach(setExpiredToken)

  it('navigates to /login when the session has expired during a query', async () => {
    renderChat()

    await userEvent.type(screen.getByPlaceholderText('Ask me anything...'), 'hello')
    await userEvent.click(screen.getByRole('button', { name: /send/i }))

    // After SESSION_EXPIRED, the app navigates to /login
    await waitFor(() =>
      expect(
        screen.getByRole('heading', { name: /sign in to your account/i })
      ).toBeInTheDocument()
    )
  })

  it('clears the access_token cookie when the session expires', async () => {
    renderChat()

    await userEvent.type(screen.getByPlaceholderText('Ask me anything...'), 'hello')
    await userEvent.click(screen.getByRole('button', { name: /send/i }))

    await waitFor(() =>
      expect(screen.getByRole('heading', { name: /sign in to your account/i })).toBeInTheDocument()
    )
    expect(document.cookie).not.toContain('access_token=expired-token')
  })
})

// ─── Logout ───────────────────────────────────────────────────────────────────

describe('Logout', () => {
  beforeEach(setValidToken)

  it('navigates to /login after clicking Logout', async () => {
    renderChat()

    await userEvent.click(screen.getByRole('button', { name: /logout/i }))

    await waitFor(() =>
      expect(
        screen.getByRole('heading', { name: /sign in to your account/i })
      ).toBeInTheDocument()
    )
  })

  it('clears the access_token cookie after logout', async () => {
    renderChat()

    await userEvent.click(screen.getByRole('button', { name: /logout/i }))

    await waitFor(() =>
      expect(screen.getByRole('heading', { name: /sign in to your account/i })).toBeInTheDocument()
    )
    expect(document.cookie).not.toContain('access_token=valid-token')
  })
})
