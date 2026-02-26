import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { submitQuery } from '../../services/agentService'
import { getAccessToken } from '../../services/authService'

vi.mock('../../services/authService')

describe('agentService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    global.fetch = vi.fn()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  // ─── submitQuery ─────────────────────────────────────────────────────────────

  describe('submitQuery', () => {
    it('throws "Not authenticated" when there is no access token', async () => {
      vi.mocked(getAccessToken).mockReturnValue(null)

      await expect(submitQuery('hello')).rejects.toThrow('Not authenticated. Please log in.')
    })

    it('returns query response on success', async () => {
      vi.mocked(getAccessToken).mockReturnValue('valid-token')
      const mockResponse = { response: 'raw answer', result: 'Formatted **answer**' }
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      const result = await submitQuery('What is React?')
      expect(result).toEqual(mockResponse)
    })

    it('sends POST to /agent/query with the prompt', async () => {
      vi.mocked(getAccessToken).mockReturnValue('valid-token')
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ response: 'ok', result: 'ok' }),
      } as Response)

      await submitQuery('my query')

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/agent/query'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ prompt: 'my query' }),
        })
      )
    })

    it('sends Authorization Bearer header with the access token', async () => {
      vi.mocked(getAccessToken).mockReturnValue('my-token')
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ response: 'ok', result: 'ok' }),
      } as Response)

      await submitQuery('hello')

      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({ Authorization: 'Bearer my-token' }),
        })
      )
    })

    it('throws SESSION_EXPIRED on 401', async () => {
      vi.mocked(getAccessToken).mockReturnValue('expired-token')
      vi.mocked(global.fetch).mockResolvedValueOnce({ ok: false, status: 401 } as Response)

      await expect(submitQuery('hello')).rejects.toThrow('SESSION_EXPIRED')
    })

    it('throws "Invalid query" on 400', async () => {
      vi.mocked(getAccessToken).mockReturnValue('valid-token')
      vi.mocked(global.fetch).mockResolvedValueOnce({ ok: false, status: 400 } as Response)

      await expect(submitQuery('bad query')).rejects.toThrow('Invalid query. Please try again.')
    })

    it('throws agent error on 500', async () => {
      vi.mocked(getAccessToken).mockReturnValue('valid-token')
      vi.mocked(global.fetch).mockResolvedValueOnce({ ok: false, status: 500 } as Response)

      await expect(submitQuery('hello')).rejects.toThrow(
        'The agent encountered an error. Please try again.'
      )
    })

    it('throws the API detail message for other non-ok status codes', async () => {
      vi.mocked(getAccessToken).mockReturnValue('valid-token')
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: false,
        status: 422,
        json: async () => ({ detail: 'Unprocessable entity' }),
      } as Response)

      await expect(submitQuery('hello')).rejects.toThrow('Unprocessable entity')
    })

    it('throws "Query timed out" when AbortError is raised', async () => {
      vi.mocked(getAccessToken).mockReturnValue('valid-token')
      vi.mocked(global.fetch).mockRejectedValueOnce(
        Object.assign(new Error('Aborted'), { name: 'AbortError' })
      )

      await expect(submitQuery('hello')).rejects.toThrow(
        'Query timed out. Please try a simpler question.'
      )
    })

    it('throws connection error when fetch itself fails', async () => {
      vi.mocked(getAccessToken).mockReturnValue('valid-token')
      vi.mocked(global.fetch).mockRejectedValueOnce(new TypeError('fetch failed'))

      await expect(submitQuery('hello')).rejects.toThrow(
        'Unable to reach the agent. Please check your connection.'
      )
    })
  })
})
