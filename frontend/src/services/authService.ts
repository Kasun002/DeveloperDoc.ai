/**
 * Authentication service for handling login, registration, and token management
 */

import { setCookie, getCookie, deleteCookie } from '../utils/cookieUtils';

// API base URL - should match backend
const API_BASE_URL = 'http://localhost:8000/api';

/**
 * Request interface for login
 */
export interface LoginRequest {
  email: string;
  password: string;
}

/**
 * Request interface for registration
 */
export interface RegisterRequest {
  email: string;
  password: string;
}

/**
 * Response interface for authentication endpoints
 */
export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

/**
 * Error response from API
 */
interface ErrorResponse {
  detail: string;
}

/**
 * Login with email and password
 * @throws Error if login fails
 */
export async function login(credentials: LoginRequest): Promise<TokenResponse> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout

    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(credentials),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error('Invalid credentials. Please try again.');
      }
      if (response.status === 500) {
        throw new Error('Server error. Please try again later.');
      }
      
      const error: ErrorResponse = await response.json().catch(() => ({
        detail: 'Login failed',
      }));
      throw new Error(error.detail || 'Login failed');
    }

    const data: TokenResponse = await response.json();
    return data;
  } catch (err) {
    if (err instanceof Error) {
      if (err.name === 'AbortError') {
        throw new Error('Request timed out. Please try again.');
      }
      if (err.message.includes('fetch')) {
        throw new Error('Unable to connect to server. Please try again.');
      }
      throw err;
    }
    throw new Error('Unable to connect to server. Please try again.');
  }
}

/**
 * Register a new user with email and password
 * @throws Error if registration fails
 */
export async function register(userData: RegisterRequest): Promise<TokenResponse> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout

    const response = await fetch(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(userData),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error('Invalid credentials. Please try again.');
      }
      if (response.status === 500) {
        throw new Error('Server error. Please try again later.');
      }
      
      const error: ErrorResponse = await response.json().catch(() => ({
        detail: 'Registration failed',
      }));
      throw new Error(error.detail || 'Registration failed');
    }

    const data: TokenResponse = await response.json();
    return data;
  } catch (err) {
    if (err instanceof Error) {
      if (err.name === 'AbortError') {
        throw new Error('Request timed out. Please try again.');
      }
      if (err.message.includes('fetch')) {
        throw new Error('Unable to connect to server. Please try again.');
      }
      throw err;
    }
    throw new Error('Unable to connect to server. Please try again.');
  }
}

/**
 * Store authentication tokens in cookies
 */
export function storeTokens(tokens: TokenResponse): void {
  const isProduction = window.location.protocol === 'https:';
  setCookie('access_token', tokens.access_token, {
    path: '/',
    secure: isProduction,
    sameSite: 'Lax',
  });
  setCookie('refresh_token', tokens.refresh_token, {
    path: '/',
    secure: isProduction,
    sameSite: 'Lax',
  });
}

/**
 * Get the access token from cookies
 * @returns The access token or null if not found
 */
export function getAccessToken(): string | null {
  return getCookie('access_token');
}

/**
 * Clear all authentication tokens from cookies
 * Used for logout
 */
export function clearTokens(): void {
  deleteCookie('access_token', { path: '/' });
  deleteCookie('refresh_token', { path: '/' });
}
