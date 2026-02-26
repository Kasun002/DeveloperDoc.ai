/**
 * E2E — Login → Chat flow
 *
 * Tests the complete journey from the login page through to using the chat.
 * All API calls are intercepted via page.route() — no real backend needed.
 */
import { test, expect } from '@playwright/test'
import {
  mockLoginSuccess,
  mockLoginFailure,
  mockQuerySuccess,
  mockQuerySessionExpired,
} from './fixtures/apiMocks'

// ─── Login page ───────────────────────────────────────────────────────────────

test.describe('Login page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
  })

  test('renders the sign-in heading', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /sign in to your account/i })).toBeVisible()
  })

  test('renders email and password inputs', async ({ page }) => {
    await expect(page.getByLabel(/email/i)).toBeVisible()
    await expect(page.getByLabel(/password/i)).toBeVisible()
  })

  test('renders the Log In button', async ({ page }) => {
    await expect(page.getByRole('button', { name: /log in/i })).toBeVisible()
  })

  test('renders a link to the register page', async ({ page }) => {
    await expect(page.getByRole('link', { name: /register here/i })).toBeVisible()
  })

  test('link to register page points to /register', async ({ page }) => {
    await page.getByRole('link', { name: /register here/i }).click()
    await expect(page).toHaveURL('/register')
  })
})

// ─── Login validation ─────────────────────────────────────────────────────────

test.describe('Login form validation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
  })

  test('shows "Email is required" when submitting with empty email', async ({ page }) => {
    await page.getByRole('button', { name: /log in/i }).click()
    await expect(page.getByText('Email is required')).toBeVisible()
  })

  test('shows "Please enter a valid email address" for bad email format', async ({ page }) => {
    await page.getByLabel(/email/i).fill('not-an-email')
    await page.getByRole('button', { name: /log in/i }).click()
    await expect(page.getByText('Please enter a valid email address')).toBeVisible()
  })

  test('shows "Password is required" when password is empty', async ({ page }) => {
    await page.getByLabel(/email/i).fill('user@example.com')
    await page.getByRole('button', { name: /log in/i }).click()
    await expect(page.getByText('Password is required')).toBeVisible()
  })
})

// ─── Login failure ────────────────────────────────────────────────────────────

test.describe('Login failure', () => {
  test.beforeEach(async ({ page }) => {
    await mockLoginFailure(page)
    await page.goto('/login')
  })

  test('shows the API error message on invalid credentials', async ({ page }) => {
    await page.getByLabel(/email/i).fill('wrong@example.com')
    await page.getByLabel(/password/i).fill('wrong123')
    await page.getByRole('button', { name: /log in/i }).click()
    await expect(page.locator('form').getByText('Invalid credentials. Please try again.')).toBeVisible()
  })

  test('stays on /login after a failed attempt', async ({ page }) => {
    await page.getByLabel(/email/i).fill('wrong@example.com')
    await page.getByLabel(/password/i).fill('wrong123')
    await page.getByRole('button', { name: /log in/i }).click()
    await page.waitForSelector('text=Invalid credentials. Please try again.')
    await expect(page).toHaveURL('/login')
  })
})

// ─── Login → Chat ─────────────────────────────────────────────────────────────

test.describe('Login → Chat', () => {
  test.beforeEach(async ({ page }) => {
    await mockLoginSuccess(page)
    await page.goto('/login')
    await page.getByLabel(/email/i).fill('test@example.com')
    await page.getByLabel(/password/i).fill('password123')
    await page.getByRole('button', { name: /log in/i }).click()
    await page.waitForURL('/chat')
  })

  test('navigates to /chat after successful login', async ({ page }) => {
    await expect(page).toHaveURL('/chat')
  })

  test('shows the DeveloperDoc.ai logo on the chat page', async ({ page }) => {
    await expect(page.getByAltText('DeveloperDoc.ai Logo')).toBeVisible()
  })

  test('shows the Logout button on the chat page', async ({ page }) => {
    await expect(page.getByRole('button', { name: /logout/i })).toBeVisible()
  })

  test('shows the prompt input and Send button', async ({ page }) => {
    await expect(page.getByPlaceholder('Ask me anything...')).toBeVisible()
    await expect(page.getByRole('button', { name: /send/i })).toBeVisible()
  })

  test('Send button is disabled when the input is empty', async ({ page }) => {
    await expect(page.getByRole('button', { name: /send/i })).toBeDisabled()
  })

  test('Send button is enabled after typing a query', async ({ page }) => {
    await page.getByPlaceholder('Ask me anything...').fill('What is React?')
    await expect(page.getByRole('button', { name: /send/i })).toBeEnabled()
  })
})

// ─── Chat — query submission ──────────────────────────────────────────────────

test.describe('Chat — query submission', () => {
  test.beforeEach(async ({ page }) => {
    await mockLoginSuccess(page)
    await page.goto('/login')
    await page.getByLabel(/email/i).fill('test@example.com')
    await page.getByLabel(/password/i).fill('password123')
    await page.getByRole('button', { name: /log in/i }).click()
    await page.waitForURL('/chat')
  })

  test('displays the response as rendered markdown after submitting a query', async ({ page }) => {
    await mockQuerySuccess(page, '## Answer\n\nThis is the answer to your question.')

    await page.getByPlaceholder('Ask me anything...').fill('What is React?')
    await page.getByRole('button', { name: /send/i }).click()

    await expect(page.getByRole('heading', { level: 2, name: /answer/i })).toBeVisible()
    await expect(page.getByText('This is the answer to your question.')).toBeVisible()
  })

  test('clears the input after a successful query', async ({ page }) => {
    await mockQuerySuccess(page)

    await page.getByPlaceholder('Ask me anything...').fill('What is React?')
    await page.getByRole('button', { name: /send/i }).click()

    await page.getByRole('heading', { level: 2, name: /answer/i }).waitFor()
    await expect(page.getByPlaceholder('Ask me anything...')).toHaveValue('')
  })

  test('redirects to /login when the session expires during a query', async ({ page }) => {
    await mockQuerySessionExpired(page)

    await page.getByPlaceholder('Ask me anything...').fill('hello')
    await page.getByRole('button', { name: /send/i }).click()

    await expect(page).toHaveURL('/login')
  })
})

// ─── Chat — logout ────────────────────────────────────────────────────────────

test.describe('Chat — logout', () => {
  test.beforeEach(async ({ page }) => {
    await mockLoginSuccess(page)
    await page.goto('/login')
    await page.getByLabel(/email/i).fill('test@example.com')
    await page.getByLabel(/password/i).fill('password123')
    await page.getByRole('button', { name: /log in/i }).click()
    await page.waitForURL('/chat')
  })

  test('navigates to /login after clicking Logout', async ({ page }) => {
    await page.getByRole('button', { name: /logout/i }).click()
    await expect(page).toHaveURL('/login')
  })

  test('cannot access /chat after logout', async ({ page }) => {
    await page.getByRole('button', { name: /logout/i }).click()
    await page.waitForURL('/login')

    await page.goto('/chat')
    await expect(page).toHaveURL('/login')
  })
})
