import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import ChatInterface from '../components/ChatInterface';

export default function ChatPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <header className="border-b border-white/10 backdrop-blur-xl bg-white/5">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 text-gray-300 hover:text-white transition-colors group"
          >
            <ArrowLeft className="w-5 h-5 group-hover:-translate-x-1 transition-transform" />
            <span className="font-medium">Back to Home</span>
          </button>
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-orange-500 to-pink-500 flex items-center justify-center font-bold">
              S
            </div>
            <div>
              <div className="text-sm font-bold text-white">Saathi (साथी)</div>
              <div className="text-xs text-gray-400">Ministry of MSME</div>
            </div>
          </div>
        </div>
      </header>

      {/* Chat Interface */}
      <main className="max-w-6xl mx-auto px-4 py-8">
        <ChatInterface />
      </main>
    </div>
  );
}
