/**
 * E2E — Register → Login → Chat flow
 *
 * After registration the app does NOT store tokens. The user is redirected
 * to /login and must sign in explicitly before accessing /chat.
 * All API calls are intercepted via page.route() — no real backend needed.
 */
import { test, expect } from '@playwright/test'
import {
  mockRegisterSuccess,
  mockRegisterFailure,
  mockLoginSuccess,
  mockQuerySuccess,
} from './fixtures/apiMocks'

// ─── Register page ────────────────────────────────────────────────────────────

test.describe('Register page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/register')
  })

  test('renders the "Create your account" heading', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /create your account/i })).toBeVisible()
  })

  test('renders email and password inputs', async ({ page }) => {
    await expect(page.getByLabel(/email/i)).toBeVisible()
    await expect(page.getByLabel(/password/i)).toBeVisible()
  })

  test('renders the Register button', async ({ page }) => {
    await expect(page.getByRole('button', { name: /^register$/i })).toBeVisible()
  })

  test('renders a link back to the login page', async ({ page }) => {
    await expect(page.getByRole('link', { name: /sign in here/i })).toBeVisible()
  })

  test('link to login page navigates to /login', async ({ page }) => {
    await page.getByRole('link', { name: /sign in here/i }).click()
    await expect(page).toHaveURL('/login')
  })
})

// ─── Register validation ──────────────────────────────────────────────────────

test.describe('Register form validation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/register')
  })

  test('shows "Email is required" when submitting an empty form', async ({ page }) => {
    await page.getByRole('button', { name: /^register$/i }).click()
    await expect(page.getByText('Email is required')).toBeVisible()
  })

  test('shows "Please enter a valid email address" for bad email format', async ({ page }) => {
    await page.getByLabel(/email/i).fill('not-an-email')
    await page.getByRole('button', { name: /^register$/i }).click()
    await expect(page.getByText('Please enter a valid email address')).toBeVisible()
  })

  test('shows "Password is required" when password is empty', async ({ page }) => {
    await page.getByLabel(/email/i).fill('new@example.com')
    await page.getByRole('button', { name: /^register$/i }).click()
    await expect(page.getByText('Password is required')).toBeVisible()
  })

  test('shows "Password must be at least 6 characters" for short passwords', async ({ page }) => {
    await page.getByLabel(/email/i).fill('new@example.com')
    await page.getByLabel(/password/i).fill('abc')
    await page.getByRole('button', { name: /^register$/i }).click()
    await expect(page.getByText('Password must be at least 6 characters')).toBeVisible()
  })
})

// ─── Register failure ─────────────────────────────────────────────────────────

test.describe('Register failure', () => {
  test.beforeEach(async ({ page }) => {
    await mockRegisterFailure(page)
    await page.goto('/register')
  })

  test('shows the API error message for an already-registered email', async ({ page }) => {
    await page.getByLabel(/email/i).fill('existing@example.com')
    await page.getByLabel(/password/i).fill('password123')
    await page.getByRole('button', { name: /^register$/i }).click()
    await expect(page.locator('form').getByText('Email already registered')).toBeVisible()
  })

  test('stays on /register after a failed attempt', async ({ page }) => {
    await page.getByLabel(/email/i).fill('existing@example.com')
    await page.getByLabel(/password/i).fill('password123')
    await page.getByRole('button', { name: /^register$/i }).click()
    await page.waitForSelector('text=Email already registered')
    await expect(page).toHaveURL('/register')
  })
})

// ─── Register success → redirect to /login ───────────────────────────────────

test.describe('Register success', () => {
  test.beforeEach(async ({ page }) => {
    await mockRegisterSuccess(page)
    await page.goto('/register')
  })

  test('redirects to /login after successful registration', async ({ page }) => {
    await page.getByLabel(/email/i).fill('new@example.com')
    await page.getByLabel(/password/i).fill('password123')
    await page.getByRole('button', { name: /^register$/i }).click()
    await expect(page).toHaveURL('/login')
  })

  test('shows the sign-in heading after redirect', async ({ page }) => {
    await page.getByLabel(/email/i).fill('new@example.com')
    await page.getByLabel(/password/i).fill('password123')
    await page.getByRole('button', { name: /^register$/i }).click()
    await expect(page.getByRole('heading', { name: /sign in to your account/i })).toBeVisible()
  })

  test('/chat is still protected immediately after registration (no token stored)', async ({
    page,
  }) => {
    await page.getByLabel(/email/i).fill('new@example.com')
    await page.getByLabel(/password/i).fill('password123')
    await page.getByRole('button', { name: /^register$/i }).click()
    await page.waitForURL('/login')

    // Try to navigate directly to /chat — should be blocked
    await page.goto('/chat')
    await expect(page).toHaveURL('/login')
  })
})

// ─── Register → Login → Chat (full flow) ─────────────────────────────────────

test.describe('Register → Login → Chat', () => {
  test('completes the full register → login → chat journey', async ({ page }) => {
    // ── Step 1: Register ──────────────────────────────────────────────────────
    await mockRegisterSuccess(page)
    await page.goto('/register')

    await page.getByLabel(/email/i).fill('newuser@example.com')
    await page.getByLabel(/password/i).fill('password123')
    await page.getByRole('button', { name: /^register$/i }).click()

    // ── Step 2: Redirected to /login ──────────────────────────────────────────
    await expect(page).toHaveURL('/login')
    await expect(page.getByRole('heading', { name: /sign in to your account/i })).toBeVisible()

    // ── Step 3: Login with registered credentials ─────────────────────────────
    await mockLoginSuccess(page)
    await page.getByLabel(/email/i).fill('newuser@example.com')
    await page.getByLabel(/password/i).fill('password123')
    await page.getByRole('button', { name: /log in/i }).click()

    // ── Step 4: Lands on /chat ────────────────────────────────────────────────
    await expect(page).toHaveURL('/chat')
    await expect(page.getByPlaceholder('Ask me anything...')).toBeVisible()
  })

  test('can submit a query after the full register → login flow', async ({ page }) => {
    // Register
    await mockRegisterSuccess(page)
    await page.goto('/register')
    await page.getByLabel(/email/i).fill('newuser@example.com')
    await page.getByLabel(/password/i).fill('password123')
    await page.getByRole('button', { name: /^register$/i }).click()

    // Login
    await mockLoginSuccess(page)
    await mockQuerySuccess(page, '## Result\n\nHere is your answer.')
    await page.waitForURL('/login')
    await page.getByLabel(/email/i).fill('newuser@example.com')
    await page.getByLabel(/password/i).fill('password123')
    await page.getByRole('button', { name: /log in/i }).click()

    // Chat
    await page.waitForURL('/chat')
    await page.getByPlaceholder('Ask me anything...').fill('What is TypeScript?')
    await page.getByRole('button', { name: /send/i }).click()

    await expect(page.getByRole('heading', { level: 2, name: /result/i })).toBeVisible()
    await expect(page.getByText('Here is your answer.')).toBeVisible()
  })

  test('can logout and login again after the full register → login flow', async ({ page }) => {
    // Register
    await mockRegisterSuccess(page)
    await page.goto('/register')
    await page.getByLabel(/email/i).fill('newuser@example.com')
    await page.getByLabel(/password/i).fill('password123')
    await page.getByRole('button', { name: /^register$/i }).click()

    // First login
    await mockLoginSuccess(page)
    await page.waitForURL('/login')
    await page.getByLabel(/email/i).fill('newuser@example.com')
    await page.getByLabel(/password/i).fill('password123')
    await page.getByRole('button', { name: /log in/i }).click()
    await page.waitForURL('/chat')

    // Logout
    await page.getByRole('button', { name: /logout/i }).click()
    await expect(page).toHaveURL('/login')

    // Login again
    await mockLoginSuccess(page)
    await page.getByLabel(/email/i).fill('newuser@example.com')
    await page.getByLabel(/password/i).fill('password123')
    await page.getByRole('button', { name: /log in/i }).click()
    await expect(page).toHaveURL('/chat')
  })
})
