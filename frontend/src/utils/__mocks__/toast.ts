import { vi } from 'vitest'

export const showSuccess = vi.fn()
export const showError = vi.fn()
export const showLoading = vi.fn(() => 'loading-toast-id')
export const showInfo = vi.fn()
export const dismissToast = vi.fn()
export const dismissAllToasts = vi.fn()
