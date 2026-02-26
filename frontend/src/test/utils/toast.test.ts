import { describe, it, expect, vi, beforeEach } from 'vitest'
import toast from 'react-hot-toast'
import { showSuccess, showError, showLoading, showInfo, dismissToast, dismissAllToasts } from '../../utils/toast'

vi.mock('react-hot-toast')

describe('toast utils', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('showSuccess', () => {
    it('calls toast.success with the message', () => {
      showSuccess('Operation done!')
      expect(toast.success).toHaveBeenCalledWith('Operation done!', expect.any(Object))
    })

    it('uses default duration of 4000ms', () => {
      showSuccess('Done')
      expect(toast.success).toHaveBeenCalledWith('Done', expect.objectContaining({ duration: 4000 }))
    })

    it('accepts a custom duration', () => {
      showSuccess('Done', 2000)
      expect(toast.success).toHaveBeenCalledWith('Done', expect.objectContaining({ duration: 2000 }))
    })
  })

  describe('showError', () => {
    it('calls toast.error with the message', () => {
      showError('Something failed')
      expect(toast.error).toHaveBeenCalledWith('Something failed', expect.any(Object))
    })

    it('uses default duration of 5000ms', () => {
      showError('Fail')
      expect(toast.error).toHaveBeenCalledWith('Fail', expect.objectContaining({ duration: 5000 }))
    })

    it('accepts a custom duration', () => {
      showError('Fail', 3000)
      expect(toast.error).toHaveBeenCalledWith('Fail', expect.objectContaining({ duration: 3000 }))
    })
  })

  describe('showLoading', () => {
    it('calls toast.loading with the message', () => {
      showLoading('Loading...')
      expect(toast.loading).toHaveBeenCalledWith('Loading...', expect.any(Object))
    })
  })

  describe('showInfo', () => {
    it('calls toast with the message', () => {
      showInfo('FYI something happened')
      expect(toast).toHaveBeenCalledWith('FYI something happened', expect.any(Object))
    })

    it('uses default duration of 4000ms', () => {
      showInfo('Info')
      expect(toast).toHaveBeenCalledWith('Info', expect.objectContaining({ duration: 4000 }))
    })

    it('accepts a custom duration', () => {
      showInfo('Info', 6000)
      expect(toast).toHaveBeenCalledWith('Info', expect.objectContaining({ duration: 6000 }))
    })
  })

  describe('dismissToast', () => {
    it('calls toast.dismiss with the given toast id', () => {
      dismissToast('toast-abc')
      expect(toast.dismiss).toHaveBeenCalledWith('toast-abc')
    })
  })

  describe('dismissAllToasts', () => {
    it('calls toast.dismiss with no arguments', () => {
      dismissAllToasts()
      expect(toast.dismiss).toHaveBeenCalledWith()
    })
  })
})
