/**
 * Agent service for handling AI agent query submissions
 */

import { getAccessToken } from './authService';

// API base URL - should match backend
const API_BASE_URL = 'http://localhost:8000/api/v1';

/**
 * Request interface for agent query
 */
export interface QueryRequest {
  query: string;
}

/**
 * Response interface for agent query
 */
export interface QueryResponse {
  response: string;
}

/**
 * Error response from API
 */
interface ErrorResponse {
  detail: string;
}

/**
 * Submit a query to the AI agent
 * @param query - The query text to submit
 * @returns The agent's response in markdown format
 * @throws Error if query submission fails or user is not authenticated
 */
export async function submitQuery(query: string): Promise<QueryResponse> {
  const accessToken = getAccessToken();
  if (!accessToken) {
    throw new Error('Not authenticated. Please log in.');
  }
  const requestBody: QueryRequest = { query };
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout for queries

    const response = await fetch(`${API_BASE_URL}/agent/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`,
      },
      body: JSON.stringify(requestBody),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error('SESSION_EXPIRED');
      }
      if (response.status === 400) {
        throw new Error('Invalid query. Please try again.');
      }
      if (response.status === 500) {
        throw new Error('The agent encountered an error. Please try again.');
      }
      
      const error: ErrorResponse = await response.json().catch(() => ({
        detail: 'Query submission failed',
      }));
      throw new Error(error.detail || 'Query submission failed');
    }

    const data: QueryResponse = await response.json();
    return data;
  } catch (err) {
    if (err instanceof Error) {
      if (err.name === 'AbortError') {
        throw new Error('Query timed out. Please try a simpler question.');
      }
      if (err.message === 'SESSION_EXPIRED') {
        throw err;
      }
      if (err.message.includes('fetch')) {
        throw new Error('Unable to reach the agent. Please check your connection.');
      }
      throw err;
    }
    throw new Error('Unable to reach the agent. Please check your connection.');
  }
}
