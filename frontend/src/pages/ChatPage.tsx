import { useNavigate } from 'react-router-dom';
import { clearTokens } from '../services/authService';
import ChatInterface from '../components/ChatInterface';

export function ChatPage() {
  const navigate = useNavigate();

  const handleLogout = () => {
    clearTokens();
    navigate('/login', { replace: true });
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-white border-b border-gray-200 px-3 py-3 sm:px-4 sm:py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <img src="/logo.png" alt="DeveloperDoc.ai Logo" className="h-8 w-auto" />
          <button
            onClick={handleLogout}
            className="ml-4 text-white bg-brand box-border border border-transparent hover:bg-brand-strong focus:ring-4 focus:ring-brand-medium shadow-xs font-medium leading-5 rounded-base text-sm px-4 py-2.5 focus:outline-none"
          >
            Logout
          </button>
        </div>
      </header>
      <main className="flex-1 overflow-hidden">
        <div className="max-w-4xl mx-auto h-full px-3 py-4 sm:px-4 sm:py-6">
          <ChatInterface />
        </div>
      </main>
    </div>
  );
}
