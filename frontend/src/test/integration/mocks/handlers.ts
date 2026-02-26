import { http, HttpResponse } from 'msw'

const AUTH_API = 'http://localhost:8000/api'
const AGENT_API = 'http://localhost:8000/api/v1'

export const handlers = [
  // ─── Auth ──────────────────────────────────────────────────────────────────

  http.post(`${AUTH_API}/auth/login`, async ({ request }) => {
    const body = await request.json() as { email: string; password: string }

    if (body.email === 'test@example.com' && body.password === 'password123') {
      return HttpResponse.json({
        access_token: 'valid-token',
        refresh_token: 'valid-refresh-token',
        token_type: 'bearer',
      })
    }

    return HttpResponse.json(
      { detail: 'Invalid credentials. Please try again.' },
      { status: 401 }
    )
  }),

  http.post(`${AUTH_API}/auth/register`, async ({ request }) => {
    const body = await request.json() as { email: string; password: string }

    if (body.email === 'existing@example.com') {
      return HttpResponse.json(
        { detail: 'Email already registered' },
        { status: 400 }
      )
    }

    return HttpResponse.json({
      access_token: 'valid-token',
      refresh_token: 'valid-refresh-token',
      token_type: 'bearer',
    })
  }),

  // ─── Agent ─────────────────────────────────────────────────────────────────

  http.post(`${AGENT_API}/agent/query`, async ({ request }) => {
    const authHeader = request.headers.get('Authorization')

    // Simulate an expired / invalid token
    if (authHeader !== 'Bearer valid-token') {
      return HttpResponse.json({ detail: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json() as { prompt: string }
    return HttpResponse.json({
      response: `Answer to: ${body.prompt}`,
      result: `## Result\n\nThis is the answer to: **${body.prompt}**`,
    })
  }),
]
