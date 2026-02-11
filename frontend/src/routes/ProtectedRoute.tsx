/**
 * ProtectedRoute component
 * Protects routes by checking for valid authentication token
 * Redirects to login if no token is found
 */

import { Navigate } from 'react-router-dom';
import { getAccessToken } from '../services/authService';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

/**
 * Wrapper component that protects routes requiring authentication
 * Checks for access_token cookie and redirects to login if not found
 */
export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const accessToken = getAccessToken();

  // If no token exists, redirect to login page
  if (!accessToken) {
    return <Navigate to="/login" replace />;
  }

  // Token exists, render the protected content
  return <>{children}</>;
}
