import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { submitQuery } from '../services/agentService';
import { clearTokens } from '../services/authService';
import MarkdownRenderer from './MarkdownRenderer';
import { showSuccess, showError, showLoading, dismissToast } from '../utils/toast';

interface QueryFormData {
  query: string;
}

const ChatInterface: React.FC = () => {
  const navigate = useNavigate();
  const [response, setResponse] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { isSubmitting },
    watch,
    reset,
  } = useForm<QueryFormData>({
    mode: 'onSubmit',
    defaultValues: {
      query: '',
    },
  });

  const queryValue = watch('query');

  const onSubmit = async (data: QueryFormData) => {
    setError(null);
    setResponse(null);
    const loadingToastId = showLoading('Submitting your query...');

    try {
      const result = await submitQuery(data.query);
      dismissToast(loadingToastId);
      showSuccess('Query submitted successfully!');
      
      setResponse(result.response);
      reset();
    } catch (err) {
      dismissToast(loadingToastId);
      const errorMessage = err instanceof Error ? err.message : 'An error occurred';
      if (errorMessage === 'SESSION_EXPIRED') {
        showError('Your session has expired. Please login again.');
        clearTokens();
        navigate('/login');
        return;
      }
      showError(errorMessage || 'Failed to submit query. Please try again.');
      setError(errorMessage);
    }
  };

  return (
    <div className="flex flex-col h-full max-h-screen">
      <form onSubmit={handleSubmit(onSubmit)} className="mb-4 sm:mb-6">
        <div className="flex flex-col sm:flex-row gap-2">
          <input
            type="text"
            {...register('query', {
              required: true,
              validate: (value) => value.trim().length > 0,
            })}
            placeholder="Ask me anything..."
            className="flex-1 px-3 py-2 sm:px-4 sm:py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 hover:border-gray-400 disabled:bg-gray-100 disabled:cursor-not-allowed text-base transition-colors"
            disabled={isSubmitting}
          />
          <button
            type="submit"
            disabled={isSubmitting || !queryValue?.trim()}
            className="px-6 py-2 sm:px-8 sm:py-3 bg-blue-600 text-white rounded-lg shadow-md hover:bg-blue-700 hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:bg-gray-400 disabled:cursor-not-allowed disabled:opacity-60 disabled:shadow-none transition-all duration-200 whitespace-nowrap font-semibold"
          >
            {isSubmitting ? 'Sending...' : 'Send'}
          </button>
        </div>
      </form>

      {/* Response Display Area */}
      <div className="flex-1 overflow-auto min-h-0">
        {isSubmitting && (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <span className="ml-3 text-gray-600">Loading...</span>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-3 sm:px-4 sm:py-4 rounded-lg">
            <p className="font-semibold text-sm sm:text-base">Error</p>
            <p className="text-sm sm:text-base">{error}</p>
          </div>
        )}

        {response && !isSubmitting && (
          <div className="bg-white border border-gray-200 rounded-lg p-4 sm:p-6">
            <MarkdownRenderer content={response} />
          </div>
        )}

        {!response && !isSubmitting && !error && (
          <div className="text-center text-gray-500 py-8">
            <p className="text-sm sm:text-base">Ask a question to get started</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatInterface;
