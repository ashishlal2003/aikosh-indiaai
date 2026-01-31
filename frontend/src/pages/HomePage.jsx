import { useNavigate } from 'react-router-dom';
import { FileText } from 'lucide-react';
import ChatInterface from '../components/ChatInterface';
import AIKoshBadge from '../components/AIKoshBadge';

export default function HomePage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <header className="text-center mb-8">
          <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
            MSME Dispute Resolution Assistant
          </h1>
          <p className="text-lg md:text-xl text-gray-700 mb-6">
            Chat with AI to resolve your payment disputes - Type or speak in any language
          </p>
        </header>

        {/* Main Content */}
        <main className="max-w-5xl mx-auto">
          <ChatInterface />

          {/* Alternative Option */}
          <div className="text-center mt-8">
            <p className="text-gray-600 mb-4">Or</p>
            <button
              onClick={() => navigate('/new-claim')}
              className="inline-flex items-center space-x-2 bg-white hover:bg-gray-50 text-gray-800 font-semibold py-3 px-6 rounded-lg shadow-md transition-colors border border-gray-200"
            >
              <FileText className="w-5 h-5" />
              <span>Upload Documents Manually</span>
            </button>
          </div>
        </main>

        {/* Footer */}
        <footer className="mt-16 pb-8">
          <AIKoshBadge />
        </footer>
      </div>
    </div>
  );
}
