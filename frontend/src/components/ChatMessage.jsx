import { Bot, User, Paperclip, Volume2 } from 'lucide-react';
import { useState, useRef } from 'react';

export default function ChatMessage({ message }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef(null);

  const isAI = message.role === 'assistant';

  const toggleAudio = () => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
      } else {
        audioRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  return (
    <div className={`flex gap-3 ${isAI ? 'justify-start' : 'justify-end'} mb-4`}>
      {isAI && (
        <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center flex-shrink-0">
          <Bot className="w-5 h-5 text-white" />
        </div>
      )}

      <div className={`max-w-[70%] ${isAI ? '' : 'order-1'}`}>
        <div
          className={`rounded-lg px-4 py-3 ${
            isAI
              ? 'bg-gray-100 text-gray-900'
              : 'bg-blue-500 text-white'
          }`}
        >
          {message.type === 'text' && (
            <p className="whitespace-pre-wrap break-words">{message.content}</p>
          )}

          {message.type === 'voice' && (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <button
                  onClick={toggleAudio}
                  className={`p-2 rounded-full ${
                    isAI ? 'bg-gray-200 hover:bg-gray-300' : 'bg-blue-600 hover:bg-blue-700'
                  }`}
                >
                  <Volume2 className="w-4 h-4" />
                </button>
                <span className="text-sm opacity-80">Voice message</span>
              </div>
              {message.transcription && (
                <p className="text-sm mt-2 italic opacity-90">{message.transcription}</p>
              )}
              {message.audioURL && (
                <audio
                  ref={audioRef}
                  src={message.audioURL}
                  onEnded={() => setIsPlaying(false)}
                  className="hidden"
                />
              )}
            </div>
          )}

          {message.type === 'document' && (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Paperclip className="w-4 h-4" />
                <span className="text-sm font-medium">{message.fileName}</span>
              </div>
              {message.extractedData && (
                <div className="mt-2 text-sm opacity-90">
                  <p className="font-semibold">Extracted info:</p>
                  <pre className="mt-1 whitespace-pre-wrap">{message.extractedData}</pre>
                </div>
              )}
            </div>
          )}

          {message.actions && message.actions.length > 0 && (
            <div className="mt-3 space-y-2">
              {message.actions.map((action, idx) => (
                <button
                  key={idx}
                  onClick={() => action.onClick && action.onClick()}
                  className="w-full bg-white text-blue-600 px-3 py-2 rounded text-sm font-medium hover:bg-gray-50 transition-colors"
                >
                  {action.label}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className={`text-xs text-gray-500 mt-1 ${isAI ? 'text-left' : 'text-right'}`}>
          {new Date(message.timestamp).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit'
          })}
        </div>
      </div>

      {!isAI && (
        <div className="w-8 h-8 rounded-full bg-gray-600 flex items-center justify-center flex-shrink-0">
          <User className="w-5 h-5 text-white" />
        </div>
      )}
    </div>
  );
}
