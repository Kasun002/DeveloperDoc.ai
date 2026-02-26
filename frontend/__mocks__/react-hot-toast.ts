import { vi } from 'vitest'

export default Object.assign(vi.fn(), {
  success: vi.fn(),
  error: vi.fn(),
  loading: vi.fn(),
  dismiss: vi.fn(),
})
