import { describe, it, expect, beforeEach } from 'vitest'
import { setCookie, getCookie, deleteCookie } from '../../utils/cookieUtils'

describe('cookieUtils', () => {
  beforeEach(() => {
    document.cookie.split(';').forEach((cookie) => {
      const name = cookie.split('=')[0].trim()
      document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`
    })
  })

  it('sets and gets a cookie', () => {
    setCookie('test', 'hello')
    expect(getCookie('test')).toBe('hello')
  })

  it('returns null for a non-existent cookie', () => {
    expect(getCookie('nonexistent')).toBeNull()
  })

  it('deletes a cookie', () => {
    setCookie('test', 'hello')
    deleteCookie('test', { path: '/' })
    expect(getCookie('test')).toBeNull()
  })
})
