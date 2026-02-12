import { useState } from 'react';
import { Send, Copy, CheckCircle, AlertCircle, Loader2, ChevronDown, ChevronUp, Mail, RotateCcw } from 'lucide-react';
import { sendEmail } from '../services/api';

const STATUS = {
  DRAFT: 'draft',
  SENDING: 'sending',
  SENT: 'sent',
  ERROR: 'error',
};

export default function EmailDraft({ emailDraft, conversationId, onEmailSent }) {
  const [status, setStatus] = useState(STATUS.DRAFT);
  const [sentAt, setSentAt] = useState(null);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const { subject, body_html, to_email, buyer_name, total_due } = emailDraft;

  const handleSend = async () => {
    if (!to_email) {
      setError('No recipient email address provided. Please ask the AI to include the buyer email.');
      setStatus(STATUS.ERROR);
      return;
    }

    setStatus(STATUS.SENDING);
    setError(null);

    try {
      const result = await sendEmail(conversationId, {
        to_email,
        subject,
        body_html,
      });

      setStatus(STATUS.SENT);
      setSentAt(result.timestamp || new Date().toISOString());
      onEmailSent?.(to_email, result.timestamp);
    } catch (err) {
      const message = err.response?.data?.detail || err.message || 'Failed to send email';
      setError(message);
      setStatus(STATUS.ERROR);
    }
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(body_html);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const textArea = document.createElement('textarea');
      textArea.value = body_html;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const bodyPreviewLength = 200;
  const strippedBody = (body_html || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
  const needsTruncation = strippedBody.length > bodyPreviewLength;

  return (
    <div className="mt-3 border border-orange-500/30 rounded-2xl bg-gradient-to-br from-orange-500/10 to-pink-500/10 overflow-hidden shadow-lg shadow-orange-500/10 backdrop-blur-lg">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-2.5 bg-white/5 border-b border-white/10 backdrop-blur-lg">
        <Mail className="w-4 h-4 text-orange-400 flex-shrink-0" />
        <span className="text-sm font-semibold text-white">Email Draft</span>
        {status === STATUS.SENT && (
          <span className="ml-auto flex items-center gap-1 text-xs text-green-400">
            <CheckCircle className="w-3.5 h-3.5" />
            Sent
          </span>
        )}
      </div>

      {/* Email fields */}
      <div className="px-4 py-3 space-y-2 text-sm">
        <div className="flex gap-2">
          <span className="text-gray-400 font-medium w-16 flex-shrink-0">To:</span>
          <span className="text-gray-100">{to_email || buyer_name || 'Not specified'}</span>
        </div>
        <div className="flex gap-2">
          <span className="text-gray-400 font-medium w-16 flex-shrink-0">Subject:</span>
          <span className="text-gray-100 break-words">{subject}</span>
        </div>

        {/* Body preview / full */}
        <div className="pt-1">
          <span className="text-gray-400 font-medium text-sm">Body:</span>
          <div className="mt-1.5 border border-white/10 rounded-lg bg-white/5 overflow-hidden backdrop-blur-lg">
            {expanded ? (
              <div
                className="px-3 py-2 text-sm email-body-preview max-h-80 overflow-y-auto text-gray-200"
                dangerouslySetInnerHTML={{ __html: body_html }}
              />
            ) : (
              <p className="px-3 py-2 text-sm text-gray-300">
                {needsTruncation ? strippedBody.slice(0, bodyPreviewLength) + '...' : strippedBody}
              </p>
            )}
          </div>
          {needsTruncation && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="flex items-center gap-1 mt-1 text-xs text-orange-400 hover:text-orange-300 transition-colors"
              aria-label={expanded ? 'Show less' : 'Show more'}
            >
              {expanded ? (
                <><ChevronUp className="w-3.5 h-3.5" /> Show less</>
              ) : (
                <><ChevronDown className="w-3.5 h-3.5" /> Show full email</>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Error message */}
      {status === STATUS.ERROR && error && (
        <div className="mx-4 mb-3 flex items-start gap-2 px-3 py-2 bg-red-500/10 border border-red-500/30 rounded-lg text-sm text-red-400">
          <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {/* Actions */}
      <div className="px-4 py-3 border-t border-white/10 flex flex-wrap gap-2">
        {status === STATUS.DRAFT && (
          <>
            <button
              onClick={handleSend}
              className="flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-orange-500 to-pink-500 hover:from-orange-600 hover:to-pink-600 text-white rounded-lg text-sm font-medium transition-all duration-300 shadow-lg shadow-orange-500/20"
              aria-label="Send email"
            >
              <Send className="w-4 h-4" />
              Send Email
            </button>
            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 px-4 py-2 bg-white/10 border border-white/20 text-gray-200 rounded-lg text-sm font-medium hover:bg-white/20 transition-all duration-300 backdrop-blur-lg"
              aria-label="Copy email to clipboard"
            >
              {copied ? (
                <><CheckCircle className="w-4 h-4 text-green-400" /> Copied</>
              ) : (
                <><Copy className="w-4 h-4" /> Copy</>
              )}
            </button>
          </>
        )}

        {status === STATUS.SENDING && (
          <button
            disabled
            className="flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-orange-400 to-pink-400 text-white rounded-lg text-sm font-medium cursor-not-allowed opacity-70"
          >
            <Loader2 className="w-4 h-4 animate-spin" />
            Sending...
          </button>
        )}

        {status === STATUS.SENT && (
          <div className="flex items-center gap-2 text-sm text-green-400">
            <CheckCircle className="w-4 h-4" />
            <span>
              Sent{sentAt && ` at ${new Date(sentAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`}
            </span>
          </div>
        )}

        {status === STATUS.ERROR && (
          <button
            onClick={handleSend}
            className="flex items-center gap-1.5 px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg text-sm font-medium transition-all duration-300 shadow-lg shadow-red-500/20"
            aria-label="Retry sending email"
          >
            <RotateCcw className="w-4 h-4" />
            Retry
          </button>
        )}
      </div>
    </div>
  );
}
