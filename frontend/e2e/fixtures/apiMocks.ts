import { type Page } from '@playwright/test'

const AUTH_API = 'http://localhost:8000/api'
const AGENT_API = 'http://localhost:8000/api/v1'

const VALID_TOKENS = {
  access_token: 'e2e-valid-token',
  refresh_token: 'e2e-refresh-token',
  token_type: 'bearer',
}

// ─── Auth mocks ───────────────────────────────────────────────────────────────

export async function mockLoginSuccess(page: Page): Promise<void> {
  await page.route(`${AUTH_API}/auth/login`, (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(VALID_TOKENS),
    })
  )
}

export async function mockLoginFailure(page: Page): Promise<void> {
  await page.route(`${AUTH_API}/auth/login`, (route) =>
    route.fulfill({
      status: 401,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Invalid credentials. Please try again.' }),
    })
  )
}

export async function mockRegisterSuccess(page: Page): Promise<void> {
  await page.route(`${AUTH_API}/auth/register`, (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(VALID_TOKENS),
    })
  )
}

export async function mockRegisterFailure(
  page: Page,
  detail = 'Email already registered'
): Promise<void> {
  await page.route(`${AUTH_API}/auth/register`, (route) =>
    route.fulfill({
      status: 400,
      contentType: 'application/json',
      body: JSON.stringify({ detail }),
    })
  )
}

// ─── Agent mocks ──────────────────────────────────────────────────────────────

export async function mockQuerySuccess(
  page: Page,
  result = '## Answer\n\nThis is the response to your question.'
): Promise<void> {
  await page.route(`${AGENT_API}/agent/query`, (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ response: result, result }),
    })
  )
}

export async function mockQuerySessionExpired(page: Page): Promise<void> {
  await page.route(`${AGENT_API}/agent/query`, (route) =>
    route.fulfill({
      status: 401,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Unauthorized' }),
    })
  )
}
