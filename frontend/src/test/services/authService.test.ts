import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { login, register, storeTokens, getAccessToken, clearTokens } from '../../services/authService'
import { setCookie, getCookie, deleteCookie } from '../../utils/cookieUtils'

vi.mock('../../utils/cookieUtils')

describe('authService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    global.fetch = vi.fn()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  // ─── login ──────────────────────────────────────────────────────────────────

  describe('login', () => {
    it('returns token response on success', async () => {
      const mockTokens = { access_token: 'at', refresh_token: 'rt', token_type: 'bearer' }
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockTokens,
      } as Response)

      const result = await login({ email: 'user@test.com', password: 'pass123' })
      expect(result).toEqual(mockTokens)
    })

    it('sends POST to /auth/login with credentials', async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ access_token: 'at', refresh_token: 'rt', token_type: 'bearer' }),
      } as Response)

      await login({ email: 'user@test.com', password: 'pass123' })

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/auth/login'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ email: 'user@test.com', password: 'pass123' }),
        })
      )
    })

    it('throws "Invalid credentials" on 401', async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce({ ok: false, status: 401 } as Response)

      await expect(login({ email: 'user@test.com', password: 'wrong' })).rejects.toThrow(
        'Invalid credentials. Please try again.'
      )
    })

    it('throws "Server error" on 500', async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce({ ok: false, status: 500 } as Response)

      await expect(login({ email: 'user@test.com', password: 'pass' })).rejects.toThrow(
        'Server error. Please try again later.'
      )
    })

    it('throws the API detail message on other non-ok responses', async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ detail: 'Account locked' }),
      } as Response)

      await expect(login({ email: 'user@test.com', password: 'pass' })).rejects.toThrow('Account locked')
    })

    it('throws "Request timed out" when AbortError is raised', async () => {
      vi.mocked(global.fetch).mockRejectedValueOnce(
        Object.assign(new Error('Aborted'), { name: 'AbortError' })
      )

      await expect(login({ email: 'user@test.com', password: 'pass' })).rejects.toThrow(
        'Request timed out. Please try again.'
      )
    })

    it('throws connection error when fetch itself fails', async () => {
      vi.mocked(global.fetch).mockRejectedValueOnce(new TypeError('fetch failed'))

      await expect(login({ email: 'user@test.com', password: 'pass' })).rejects.toThrow(
        'Unable to connect to server. Please try again.'
      )
    })
  })

  // ─── register ───────────────────────────────────────────────────────────────

  describe('register', () => {
    it('returns token response on success', async () => {
      const mockTokens = { access_token: 'at', refresh_token: 'rt', token_type: 'bearer' }
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockTokens,
      } as Response)

      const result = await register({ email: 'new@test.com', password: 'pass123' })
      expect(result).toEqual(mockTokens)
    })

    it('sends POST to /auth/register with user data', async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ access_token: 'at', refresh_token: 'rt', token_type: 'bearer' }),
      } as Response)

      await register({ email: 'new@test.com', password: 'pass123' })

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/auth/register'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ email: 'new@test.com', password: 'pass123' }),
        })
      )
    })

    it('throws "Server error" on 500', async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce({ ok: false, status: 500 } as Response)

      await expect(register({ email: 'new@test.com', password: 'pass' })).rejects.toThrow(
        'Server error. Please try again later.'
      )
    })

    it('throws the API detail message on 400', async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ detail: 'Email already registered' }),
      } as Response)

      await expect(register({ email: 'existing@test.com', password: 'pass' })).rejects.toThrow(
        'Email already registered'
      )
    })

    it('throws "Request timed out" on AbortError', async () => {
      vi.mocked(global.fetch).mockRejectedValueOnce(
        Object.assign(new Error('Aborted'), { name: 'AbortError' })
      )

      await expect(register({ email: 'new@test.com', password: 'pass' })).rejects.toThrow(
        'Request timed out. Please try again.'
      )
    })

    it('throws connection error when fetch itself fails', async () => {
      vi.mocked(global.fetch).mockRejectedValueOnce(new TypeError('fetch failed'))

      await expect(register({ email: 'new@test.com', password: 'pass' })).rejects.toThrow(
        'Unable to connect to server. Please try again.'
      )
    })
  })

  // ─── storeTokens ────────────────────────────────────────────────────────────

  describe('storeTokens', () => {
    it('stores access_token in cookie', () => {
      storeTokens({ access_token: 'at', refresh_token: 'rt', token_type: 'bearer' })
      expect(setCookie).toHaveBeenCalledWith('access_token', 'at', expect.any(Object))
    })

    it('stores refresh_token in cookie', () => {
      storeTokens({ access_token: 'at', refresh_token: 'rt', token_type: 'bearer' })
      expect(setCookie).toHaveBeenCalledWith('refresh_token', 'rt', expect.any(Object))
    })
  })

  // ─── getAccessToken ─────────────────────────────────────────────────────────

  describe('getAccessToken', () => {
    it('returns the token from cookie', () => {
      vi.mocked(getCookie).mockReturnValue('my-access-token')
      expect(getAccessToken()).toBe('my-access-token')
      expect(getCookie).toHaveBeenCalledWith('access_token')
    })

    it('returns null when cookie is not set', () => {
      vi.mocked(getCookie).mockReturnValue(null)
      expect(getAccessToken()).toBeNull()
    })
  })

  // ─── clearTokens ────────────────────────────────────────────────────────────

  describe('clearTokens', () => {
    it('deletes access_token cookie', () => {
      clearTokens()
      expect(deleteCookie).toHaveBeenCalledWith('access_token', expect.any(Object))
    })

    it('deletes refresh_token cookie', () => {
      clearTokens()
      expect(deleteCookie).toHaveBeenCalledWith('refresh_token', expect.any(Object))
    })
  })
})
