/**
 * Toast notification utility
 * Provides helper functions for showing toast notifications
 */

import toast from 'react-hot-toast';

/**
 * Show a success toast notification
 * @param message - The success message to display
 * @param duration - Duration in milliseconds (default: 4000)
 */
export const showSuccess = (message: string, duration: number = 4000) => {
  return toast.success(message, {
    duration,
    position: 'top-right',
    style: {
      background: '#10B981',
      color: '#fff',
      padding: '16px',
      borderRadius: '8px',
      fontSize: '14px',
      fontWeight: '500',
    },
    iconTheme: {
      primary: '#fff',
      secondary: '#10B981',
    },
  });
};

/**
 * Show an error toast notification
 * @param message - The error message to display
 * @param duration - Duration in milliseconds (default: 5000)
 */
export const showError = (message: string, duration: number = 5000) => {
  return toast.error(message, {
    duration,
    position: 'top-right',
    style: {
      background: '#EF4444',
      color: '#fff',
      padding: '16px',
      borderRadius: '8px',
      fontSize: '14px',
      fontWeight: '500',
    },
    iconTheme: {
      primary: '#fff',
      secondary: '#EF4444',
    },
  });
};

/**
 * Show a loading toast notification
 * @param message - The loading message to display
 * @returns Toast ID that can be used to dismiss the toast later
 */
export const showLoading = (message: string) => {
  return toast.loading(message, {
    position: 'top-right',
    style: {
      background: '#3B82F6',
      color: '#fff',
      padding: '16px',
      borderRadius: '8px',
      fontSize: '14px',
      fontWeight: '500',
    },
  });
};

/**
 * Show an info toast notification
 * @param message - The info message to display
 * @param duration - Duration in milliseconds (default: 4000)
 */
export const showInfo = (message: string, duration: number = 4000) => {
  return toast(message, {
    duration,
    position: 'top-right',
    icon: 'ℹ️',
    style: {
      background: '#3B82F6',
      color: '#fff',
      padding: '16px',
      borderRadius: '8px',
      fontSize: '14px',
      fontWeight: '500',
    },
  });
};

/**
 * Dismiss a specific toast by ID
 * @param toastId - The ID of the toast to dismiss
 */
export const dismissToast = (toastId: string) => {
  toast.dismiss(toastId);
};

/**
 * Dismiss all active toasts
 */
export const dismissAllToasts = () => {
  toast.dismiss();
};
