/**
 * Routing integration tests
 *
 * Tests AppRouter + ProtectedRoute guard behaviour.
 * Verifies that routes redirect correctly based on auth state.
 */
import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
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

const renderAt = (route: string) =>
  render(
    <MemoryRouter initialEntries={[route]}>
      <AppRouter />
    </MemoryRouter>
  )

const setValidToken = () => {
  document.cookie = 'access_token=valid-token; path=/'
}

// ─── Root redirect ────────────────────────────────────────────────────────────

describe('Root redirect (/)', () => {
  it('redirects unauthenticated users from / to /login', () => {
    renderAt('/')
    expect(screen.getByRole('heading', { name: /sign in to your account/i })).toBeInTheDocument()
  })

  it('redirects authenticated users from / to /chat', () => {
    setValidToken()
    renderAt('/')
    expect(screen.getByAltText('DeveloperDoc.ai Logo')).toBeInTheDocument()
  })
})

// ─── Protected route (/chat) ──────────────────────────────────────────────────

describe('Protected route (/chat)', () => {
  it('redirects unauthenticated users from /chat to /login', () => {
    renderAt('/chat')
    expect(screen.getByRole('heading', { name: /sign in to your account/i })).toBeInTheDocument()
  })

  it('renders the chat page for authenticated users', () => {
    setValidToken()
    renderAt('/chat')
    expect(screen.getByAltText('DeveloperDoc.ai Logo')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /logout/i })).toBeInTheDocument()
  })
})

// ─── Public routes ────────────────────────────────────────────────────────────

describe('Public routes', () => {
  it('renders /login without a token', () => {
    renderAt('/login')
    expect(screen.getByRole('heading', { name: /sign in to your account/i })).toBeInTheDocument()
  })

  it('renders /register without a token', () => {
    renderAt('/register')
    expect(screen.getByRole('heading', { name: /create your account/i })).toBeInTheDocument()
  })

  it('renders /login even when a token is present', () => {
    setValidToken()
    renderAt('/login')
    expect(screen.getByRole('heading', { name: /sign in to your account/i })).toBeInTheDocument()
  })

  it('renders /register even when a token is present', () => {
    setValidToken()
    renderAt('/register')
    expect(screen.getByRole('heading', { name: /create your account/i })).toBeInTheDocument()
  })
})
