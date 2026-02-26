import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import ChatInterface from '../../components/ChatInterface'

const mockNavigate = vi.fn()

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => mockNavigate }
})

vi.mock('../../services/agentService')
vi.mock('../../services/authService')
vi.mock('../../utils/toast')

import { submitQuery } from '../../services/agentService'
import { clearTokens } from '../../services/authService'
import { showLoading, dismissToast, showSuccess, showError } from '../../utils/toast'

describe('ChatInterface', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  const renderComponent = () =>
    render(
      <MemoryRouter>
        <ChatInterface />
      </MemoryRouter>
    )

  // ─── Rendering ───────────────────────────────────────────────────────────────

  describe('rendering', () => {
    it('renders the prompt text input', () => {
      renderComponent()
      expect(screen.getByPlaceholderText('Ask me anything...')).toBeInTheDocument()
    })

    it('renders the Send button', () => {
      renderComponent()
      expect(screen.getByRole('button', { name: /send/i })).toBeInTheDocument()
    })

    it('shows the empty state message when no query has been submitted', () => {
      renderComponent()
      expect(screen.getByText('Ask a question to get started')).toBeInTheDocument()
    })

    it('Send button is disabled when the input is empty', () => {
      renderComponent()
      expect(screen.getByRole('button', { name: /send/i })).toBeDisabled()
    })

    it('Send button is enabled after typing in the input', async () => {
      renderComponent()
      await userEvent.type(screen.getByPlaceholderText('Ask me anything...'), 'hello')
      expect(screen.getByRole('button', { name: /send/i })).not.toBeDisabled()
    })
  })

  // ─── Successful query ─────────────────────────────────────────────────────────

  describe('successful query submission', () => {
    it('displays the response content after a successful query', async () => {
      vi.mocked(submitQuery).mockResolvedValueOnce({
        response: 'raw',
        result: 'This is the answer from the agent',
      })

      renderComponent()
      await userEvent.type(screen.getByPlaceholderText('Ask me anything...'), 'What is React?')
      await userEvent.click(screen.getByRole('button', { name: /send/i }))

      expect(await screen.findByText('This is the answer from the agent')).toBeInTheDocument()
    })

    it('calls submitQuery with the typed prompt', async () => {
      vi.mocked(submitQuery).mockResolvedValueOnce({ response: 'ok', result: 'Answer' })

      renderComponent()
      await userEvent.type(screen.getByPlaceholderText('Ask me anything...'), 'my question')
      await userEvent.click(screen.getByRole('button', { name: /send/i }))

      await waitFor(() => expect(submitQuery).toHaveBeenCalledWith('my question'))
    })

    it('shows loading toast when submitting', async () => {
      vi.mocked(submitQuery).mockResolvedValueOnce({ response: 'ok', result: 'Answer' })

      renderComponent()
      await userEvent.type(screen.getByPlaceholderText('Ask me anything...'), 'hello')
      await userEvent.click(screen.getByRole('button', { name: /send/i }))

      await waitFor(() => expect(showLoading).toHaveBeenCalledWith('Submitting your query...'))
    })

    it('dismisses the loading toast after a successful query', async () => {
      vi.mocked(submitQuery).mockResolvedValueOnce({ response: 'ok', result: 'Answer' })

      renderComponent()
      await userEvent.type(screen.getByPlaceholderText('Ask me anything...'), 'hello')
      await userEvent.click(screen.getByRole('button', { name: /send/i }))

      await waitFor(() => expect(dismissToast).toHaveBeenCalledWith('loading-toast-id'))
    })

    it('calls showSuccess after a successful query', async () => {
      vi.mocked(submitQuery).mockResolvedValueOnce({ response: 'ok', result: 'Answer' })

      renderComponent()
      await userEvent.type(screen.getByPlaceholderText('Ask me anything...'), 'hello')
      await userEvent.click(screen.getByRole('button', { name: /send/i }))

      await waitFor(() =>
        expect(showSuccess).toHaveBeenCalledWith('Query submitted successfully!')
      )
    })

    it('clears the input after a successful query', async () => {
      vi.mocked(submitQuery).mockResolvedValueOnce({ response: 'ok', result: 'Answer' })

      renderComponent()
      const input = screen.getByPlaceholderText('Ask me anything...')
      await userEvent.type(input, 'hello')
      await userEvent.click(screen.getByRole('button', { name: /send/i }))

      await waitFor(() => expect(input).toHaveValue(''))
    })
  })

  // ─── Failed query ─────────────────────────────────────────────────────────────

  describe('failed query submission', () => {
    it('displays the error message on a failed query', async () => {
      vi.mocked(submitQuery).mockRejectedValueOnce(new Error('Something went wrong'))

      renderComponent()
      await userEvent.type(screen.getByPlaceholderText('Ask me anything...'), 'hello')
      await userEvent.click(screen.getByRole('button', { name: /send/i }))

      expect(await screen.findByText('Something went wrong')).toBeInTheDocument()
    })

    it('shows the Error heading when a query fails', async () => {
      vi.mocked(submitQuery).mockRejectedValueOnce(new Error('Network error'))

      renderComponent()
      await userEvent.type(screen.getByPlaceholderText('Ask me anything...'), 'hello')
      await userEvent.click(screen.getByRole('button', { name: /send/i }))

      expect(await screen.findByText('Error')).toBeInTheDocument()
    })

    it('calls showError with the error message on failure', async () => {
      vi.mocked(submitQuery).mockRejectedValueOnce(new Error('Agent error'))

      renderComponent()
      await userEvent.type(screen.getByPlaceholderText('Ask me anything...'), 'hello')
      await userEvent.click(screen.getByRole('button', { name: /send/i }))

      await waitFor(() => expect(showError).toHaveBeenCalledWith('Agent error'))
    })

    it('dismisses the loading toast after a failed query', async () => {
      vi.mocked(submitQuery).mockRejectedValueOnce(new Error('fail'))

      renderComponent()
      await userEvent.type(screen.getByPlaceholderText('Ask me anything...'), 'hello')
      await userEvent.click(screen.getByRole('button', { name: /send/i }))

      await waitFor(() => expect(dismissToast).toHaveBeenCalledWith('loading-toast-id'))
    })
  })

  // ─── Session expired ──────────────────────────────────────────────────────────

  describe('SESSION_EXPIRED handling', () => {
    it('calls clearTokens when the session has expired', async () => {
      vi.mocked(submitQuery).mockRejectedValueOnce(new Error('SESSION_EXPIRED'))

      renderComponent()
      await userEvent.type(screen.getByPlaceholderText('Ask me anything...'), 'hello')
      await userEvent.click(screen.getByRole('button', { name: /send/i }))

      await waitFor(() => expect(clearTokens).toHaveBeenCalled())
    })

    it('navigates to /login when the session has expired', async () => {
      vi.mocked(submitQuery).mockRejectedValueOnce(new Error('SESSION_EXPIRED'))

      renderComponent()
      await userEvent.type(screen.getByPlaceholderText('Ask me anything...'), 'hello')
      await userEvent.click(screen.getByRole('button', { name: /send/i }))

      await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/login'))
    })

    it('shows the session expired error toast', async () => {
      vi.mocked(submitQuery).mockRejectedValueOnce(new Error('SESSION_EXPIRED'))

      renderComponent()
      await userEvent.type(screen.getByPlaceholderText('Ask me anything...'), 'hello')
      await userEvent.click(screen.getByRole('button', { name: /send/i }))

      await waitFor(() =>
        expect(showError).toHaveBeenCalledWith('Your session has expired. Please login again.')
      )
    })
  })
})
