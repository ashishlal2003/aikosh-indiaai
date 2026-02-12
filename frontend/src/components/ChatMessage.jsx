import { Bot, User, Paperclip, Volume2, Wrench } from 'lucide-react';
import { useState, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import EmailDraft from './EmailDraft';

export default function ChatMessage({ message, conversationId, onEmailSent }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef(null);

  const isAI = message.role === 'assistant';

  // Get friendly tool name for display
  const getToolDisplayName = (toolName) => {
    const toolNames = {
      'calculate_msme_interest': 'Calculating interest',
      'verify_document': 'Verifying document',
      'draft_demand_notice_email': 'Drafting email',
      'get_current_date': 'Getting current date',
    };
    return toolNames[toolName] || 'Processing';
  };

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
    <div className={`flex gap-3 ${isAI ? 'justify-start' : 'justify-end'}`}>
      {isAI && (
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-orange-500 to-pink-500 flex items-center justify-center flex-shrink-0 shadow-lg shadow-orange-500/20">
          <Bot className="w-5 h-5 text-white" />
        </div>
      )}

      <div className={`max-w-[70%] ${isAI ? '' : 'order-1'}`}>
        <div
          className={`rounded-2xl px-5 py-3.5 backdrop-blur-xl border transition-all duration-300 ${
            isAI
              ? 'bg-white/5 border-white/10 text-gray-100 hover:bg-white/10'
              : 'bg-gradient-to-r from-orange-500 to-pink-500 border-white/20 text-white shadow-lg shadow-orange-500/20'
          }`}
        >
          {/* Tool execution indicator */}
          {message.toolExecuting && (
            <div className="mb-2 flex items-center gap-2 px-3 py-2 bg-orange-500/10 border border-orange-500/30 rounded-lg">
              <Wrench className="w-4 h-4 text-orange-400 animate-pulse" />
              <span className="text-xs text-orange-300 font-medium">
                {getToolDisplayName(message.toolExecuting)}...
              </span>
            </div>
          )}

          {message.type === 'text' && (
            <div className="prose prose-sm max-w-none break-words prose-invert">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeRaw]}
                components={{
                  // Style paragraphs
                  p: ({ node, ...props }) => <p className="mb-2 last:mb-0 text-inherit" {...props} />,
                  // Style lists
                  ul: ({ node, ...props }) => <ul className="list-disc ml-4 mb-2 text-inherit" {...props} />,
                  ol: ({ node, ...props }) => <ol className="list-decimal ml-4 mb-2 text-inherit" {...props} />,
                  li: ({ node, ...props }) => <li className="mb-1 text-inherit" {...props} />,
                  // Style links
                  a: ({ node, ...props }) => (
                    <a
                      className={`${
                        isAI ? 'text-orange-400 hover:text-orange-300' : 'text-white hover:text-gray-100'
                      } underline underline-offset-2`}
                      target="_blank"
                      rel="noopener noreferrer"
                      {...props}
                    />
                  ),
                  // Style code blocks
                  code: ({ node, inline, ...props }) =>
                    inline ? (
                      <code className="bg-white/10 px-1.5 py-0.5 rounded text-sm font-mono text-inherit" {...props} />
                    ) : (
                      <code className="block bg-white/10 p-3 rounded-lg text-sm font-mono overflow-x-auto text-inherit my-2" {...props} />
                    ),
                  // Style headings
                  h1: ({ node, ...props }) => <h1 className="text-xl font-bold mb-2 text-inherit" {...props} />,
                  h2: ({ node, ...props }) => <h2 className="text-lg font-bold mb-2 text-inherit" {...props} />,
                  h3: ({ node, ...props }) => <h3 className="text-base font-bold mb-1 text-inherit" {...props} />,
                  // Style blockquotes
                  blockquote: ({ node, ...props }) => (
                    <blockquote className="border-l-4 border-orange-400/50 pl-3 italic my-2 text-inherit" {...props} />
                  ),
                  // Style horizontal rules
                  hr: ({ node, ...props }) => <hr className="my-3 border-white/20" {...props} />,
                  // Style tables
                  table: ({ node, ...props }) => (
                    <table className="border-collapse border border-white/20 my-2 text-inherit" {...props} />
                  ),
                  th: ({ node, ...props }) => (
                    <th className="border border-white/20 px-2 py-1 bg-white/5 font-semibold text-inherit" {...props} />
                  ),
                  td: ({ node, ...props }) => <td className="border border-white/20 px-2 py-1 text-inherit" {...props} />,
                }}
              >
                {message.content}
              </ReactMarkdown>
              {/* Streaming cursor */}
              {message.isStreaming && (
                <span className="inline-block w-1.5 h-4 bg-orange-400 ml-0.5 animate-pulse"></span>
              )}
            </div>
          )}

          {message.type === 'voice' && (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <button
                  onClick={toggleAudio}
                  className={`p-2 rounded-lg transition-all duration-300 ${
                    isAI
                      ? 'bg-white/10 hover:bg-white/20'
                      : 'bg-white/20 hover:bg-white/30'
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
                  <pre className="mt-1 whitespace-pre-wrap bg-white/5 p-2 rounded-lg">{message.extractedData}</pre>
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
                  className="w-full bg-white/10 backdrop-blur-lg border border-white/20 text-white px-3 py-2 rounded-lg text-sm font-medium hover:bg-white/20 transition-all duration-300"
                >
                  {action.label}
                </button>
              ))}
            </div>
          )}
        </div>

        {message.emailDraft && (
          <EmailDraft
            emailDraft={message.emailDraft}
            conversationId={conversationId}
            onEmailSent={onEmailSent}
          />
        )}

        <div className={`text-xs text-gray-400 mt-1.5 ${isAI ? 'text-left' : 'text-right'}`}>
          {new Date(message.timestamp).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit'
          })}
        </div>
      </div>

      {!isAI && (
        <div className="w-9 h-9 rounded-xl bg-white/10 backdrop-blur-lg border border-white/20 flex items-center justify-center flex-shrink-0">
          <User className="w-5 h-5 text-gray-300" />
        </div>
      )}
    </div>
  );
}
