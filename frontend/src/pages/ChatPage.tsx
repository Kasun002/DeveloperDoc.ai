/**
 * ChatPage component
 * Renders the chat interface with ChatGPT-like layout
 */

import ChatInterface from '../components/ChatInterface';

export function ChatPage() {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-3 py-3 sm:px-4 sm:py-4">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-lg sm:text-xl font-semibold text-gray-800">AI Chat Assistant</h1>
        </div>
      </header>

      {/* Main Chat Area */}
      <main className="flex-1 overflow-hidden">
        <div className="max-w-4xl mx-auto h-full px-3 py-4 sm:px-4 sm:py-6">
          <ChatInterface />
        </div>
      </main>
    </div>
  );
}
