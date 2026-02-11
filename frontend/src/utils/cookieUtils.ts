/**
 * Cookie utility functions for managing browser cookies
 */

export interface CookieOptions {
  expires?: Date | number; // Date object or days from now
  path?: string;
  domain?: string;
  secure?: boolean;
  sameSite?: 'Strict' | 'Lax' | 'None';
  httpOnly?: boolean; // Note: httpOnly cannot be set from JavaScript, included for completeness
}

/**
 * Set a cookie with the specified name, value, and options
 */
export function setCookie(name: string, value: string, options: CookieOptions = {}): void {
  let cookieString = `${encodeURIComponent(name)}=${encodeURIComponent(value)}`;

  // Handle expires option
  if (options.expires) {
    let expiresDate: Date;
    if (typeof options.expires === 'number') {
      // Convert days to date
      expiresDate = new Date();
      expiresDate.setTime(expiresDate.getTime() + options.expires * 24 * 60 * 60 * 1000);
    } else {
      expiresDate = options.expires;
    }
    cookieString += `; expires=${expiresDate.toUTCString()}`;
  }

  // Handle path option (default to '/')
  cookieString += `; path=${options.path || '/'}`;

  // Handle domain option
  if (options.domain) {
    cookieString += `; domain=${options.domain}`;
  }

  // Handle secure option
  if (options.secure) {
    cookieString += '; secure';
  }

  // Handle sameSite option
  if (options.sameSite) {
    cookieString += `; samesite=${options.sameSite}`;
  }

  // Note: httpOnly cannot be set from JavaScript for security reasons
  // It can only be set by the server in Set-Cookie header

  document.cookie = cookieString;
}

/**
 * Get a cookie value by name
 * Returns null if the cookie doesn't exist
 */
export function getCookie(name: string): string | null {
  const nameEQ = encodeURIComponent(name) + '=';
  const cookies = document.cookie.split(';');

  for (let i = 0; i < cookies.length; i++) {
    let cookie = cookies[i];
    // Trim leading spaces
    while (cookie.charAt(0) === ' ') {
      cookie = cookie.substring(1);
    }
    // Check if this cookie matches the name we're looking for
    if (cookie.indexOf(nameEQ) === 0) {
      return decodeURIComponent(cookie.substring(nameEQ.length));
    }
  }

  return null;
}

/**
 * Delete a cookie by name
 * Sets the cookie's expiration date to the past
 */
export function deleteCookie(name: string, options: Pick<CookieOptions, 'path' | 'domain'> = {}): void {
  setCookie(name, '', {
    ...options,
    expires: new Date(0), // Set to epoch time (Jan 1, 1970)
  });
}
