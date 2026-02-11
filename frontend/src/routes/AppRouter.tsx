/**
 * AppRouter component
 * Defines all application routes and handles authentication-based redirects
 */

import { Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from '../pages/LoginPage';
import RegisterPage from '../pages/RegisterPage';
import { ChatPage } from '../pages/ChatPage';
import { ProtectedRoute } from './ProtectedRoute';
import { getAccessToken } from '../services/authService';

/**
 * Root redirect component
 * Redirects to /chat if authenticated, otherwise to /login
 */
function RootRedirect() {
  const accessToken = getAccessToken();
  
  if (accessToken) {
    return <Navigate to="/chat" replace />;
  }
  
  return <Navigate to="/login" replace />;
}

/**
 * Main application router
 * Defines all routes and implements authentication-based routing
 */
export function AppRouter() {
  return (
    <Routes>
      {/* Root path - redirect based on authentication */}
      <Route path="/" element={<RootRedirect />} />
      
      {/* Public routes */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      
      {/* Protected routes */}
      <Route
        path="/chat"
        element={
          <ProtectedRoute>
            <ChatPage />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
