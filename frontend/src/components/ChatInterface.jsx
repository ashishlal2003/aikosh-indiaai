import { useState, useRef, useEffect } from 'react';
import { Loader2, Wrench } from 'lucide-react';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import ClaimProgress from './ClaimProgress';
import { sendChatMessage, sendChatMessageStream, transcribeAudio, uploadChatDocument } from '../services/api';

export default function ChatInterface() {
  const [messages, setMessages] = useState([
    {
      id: 1,
      role: 'assistant',
      type: 'text',
      content: "Namaste! I'm Saathi (साथी), your AI Dispute Resolution Assistant from MoMSME, Government of India. I'm here to help you recover your delayed payments under the MSMED Act. Tell me about your payment dispute - you can type or speak in any language.",
      timestamp: new Date().toISOString(),
    }
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const [completeness, setCompleteness] = useState(null);
  const [selectedLanguage, setSelectedLanguage] = useState('en');
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const triggered100Ref = useRef(false);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Auto-trigger email drafting when all required docs are verified
  useEffect(() => {
    if (
      completeness?.completeness_percentage === 100 &&
      !triggered100Ref.current
    ) {
      triggered100Ref.current = true;
      getAIResponse(
        'All required documents have been uploaded and verified. Please draft the demand notice email to the buyer now.',
        'text'
      );
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [completeness]);

  // Generate conversation ID on first load
  useEffect(() => {
    setConversationId('conv_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9));
  }, []);

  const addMessage = (message) => {
    setMessages(prev => [...prev, {
      ...message,
      id: Date.now() + Math.random(),
      timestamp: new Date().toISOString(),
    }]);
  };

  const handleSendTextMessage = async (text) => {
    // Add user message
    addMessage({
      role: 'user',
      type: 'text',
      content: text,
    });

    // Get AI response
    await getAIResponse(text, 'text');
  };

  const handleSendVoiceMessage = async (audioBlob, audioURL) => {
    try {
      // Add temporary voice message
      addMessage({
        role: 'user',
        type: 'voice',
        content: 'Voice message',
        audioURL: audioURL,
        transcription: 'Transcribing...',
      });

      setIsLoading(true);

      // Transcribe audio
      const transcriptionResult = await transcribeAudio(audioBlob, selectedLanguage, conversationId);
      const transcribedText = transcriptionResult.text;

      // Update the last message with transcription
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1].transcription = transcribedText;
        return updated;
      });

      // Get AI response based on transcription
      await getAIResponse(transcribedText, 'voice');

    } catch (error) {
      console.error('Error processing voice message:', error);
      addMessage({
        role: 'assistant',
        type: 'text',
        content: 'Sorry, I had trouble processing your voice message. Please try again or type your message.',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleUploadDocument = async (file) => {
    try {
      // Add document message
      addMessage({
        role: 'user',
        type: 'document',
        content: 'Document uploaded',
        fileName: file.name,
      });

      setIsLoading(true);

      // Upload and process document
      const result = await uploadChatDocument(file, conversationId);

      // Update document message with extracted data
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1].extractedData = result.extracted_data || 'Processing document...';
        return updated;
      });

      // Update completeness progress bar (doc is pending until AI verifies)
      if (result.completeness) setCompleteness(result.completeness);

      // Get AI response about the document
      await getAIResponse(`I uploaded a document: ${file.name}`, 'document', result.extracted_data);

    } catch (error) {
      console.error('Error uploading document:', error);
      addMessage({
        role: 'assistant',
        type: 'text',
        content: 'Sorry, I had trouble processing your document. Please try again.',
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Handle action button clicks
  const handleActionClick = (actionType) => {
    const actionLower = actionType.toLowerCase();

    // Upload document actions
    if (actionLower.includes('upload') || actionLower.includes('document')) {
      fileInputRef.current?.click();
      return;
    }

    // Draft email action - send as user message
    if (actionLower.includes('draft') || actionLower.includes('email')) {
      handleSendTextMessage('Please draft an email to the buyer requesting payment');
      return;
    }

    // Calculate interest action
    if (actionLower.includes('interest') || actionLower.includes('calculate')) {
      handleSendTextMessage('Calculate the interest I am owed under MSMED Act Section 15');
      return;
    }

    // File complaint / ODR action
    if (actionLower.includes('file') || actionLower.includes('complaint') || actionLower.includes('odr')) {
      handleSendTextMessage('How do I file a complaint with the MSME Facilitation Council?');
      return;
    }

    // Default: send as question
    handleSendTextMessage(actionType);
  };

  const getAIResponse = async (userMessage, messageType, documentData = null) => {
    // Create a placeholder message for streaming
    const placeholderMessageId = Date.now() + Math.random();
    const placeholderMessage = {
      id: placeholderMessageId,
      role: 'assistant',
      type: 'text',
      content: '',
      timestamp: new Date().toISOString(),
      isStreaming: true,
    };

    setMessages(prev => [...prev, placeholderMessage]);
    setIsLoading(true);

    try {
      // Prepare conversation history for API
      const conversationHistory = messages.map(msg => ({
        role: msg.role,
        content: msg.type === 'text' ? msg.content : (msg.transcription || msg.content)
      }));

      // Add current message
      conversationHistory.push({
        role: 'user',
        content: userMessage
      });

      // Add document context if available
      if (documentData) {
        conversationHistory[conversationHistory.length - 1].content +=
          `\n\nDocument Data: ${documentData}`;
      }

      // Variables to accumulate streaming response
      let fullContent = '';
      let finalActions = [];
      let finalEmailDraft = null;
      let finalCompleteness = null;

      // Stream the response
      await sendChatMessageStream(
        {
          conversation_id: conversationId,
          messages: conversationHistory,
          message_type: messageType
        },
        (eventType, data) => {
          if (eventType === 'tool_start') {
            // Show tool execution indicator
            setMessages(prev => prev.map(msg =>
              msg.id === placeholderMessageId
                ? { ...msg, toolExecuting: data.tool }
                : msg
            ));
          }
          else if (eventType === 'tool_end') {
            // Clear tool execution indicator
            setMessages(prev => prev.map(msg =>
              msg.id === placeholderMessageId
                ? { ...msg, toolExecuting: null }
                : msg
            ));
          }
          else if (eventType === 'message') {
            // Append streamed content token
            fullContent += data.content;
            setMessages(prev => prev.map(msg =>
              msg.id === placeholderMessageId
                ? { ...msg, content: fullContent }
                : msg
            ));
          }
          else if (eventType === 'done') {
            // Finalize message with actions and metadata
            finalActions = data.actions || [];
            finalEmailDraft = data.email_draft;
            finalCompleteness = data.completeness;

            // Update completeness if available
            if (finalCompleteness) setCompleteness(finalCompleteness);

            // Map actions to handlers
            const mappedActions = finalActions
              .filter(action => action.type !== 'send_email')
              .map(action => ({
                label: action.label,
                onClick: () => handleActionClick(action.action || action.label),
              }));

            // Finalize the message
            setMessages(prev => prev.map(msg =>
              msg.id === placeholderMessageId
                ? {
                    ...msg,
                    content: fullContent,
                    actions: mappedActions,
                    emailDraft: finalEmailDraft,
                    isStreaming: false,
                    toolExecuting: null,
                  }
                : msg
            ));
          }
          else if (eventType === 'error') {
            console.error('Streaming error:', data);
            setMessages(prev => prev.map(msg =>
              msg.id === placeholderMessageId
                ? {
                    ...msg,
                    content: 'Sorry, I encountered an error. Please try again.',
                    isStreaming: false,
                    toolExecuting: null,
                  }
                : msg
            ));
          }
        }
      );

    } catch (error) {
      console.error('Error getting AI response:', error);
      setMessages(prev => prev.map(msg =>
        msg.id === placeholderMessageId
          ? {
              ...msg,
              content: 'Sorry, I encountered an error. Please try again.',
              isStreaming: false,
              toolExecuting: null,
            }
          : msg
      ));
    } finally {
      setIsLoading(false);
    }
  };

  const handleEmailSent = (toEmail, timestamp) => {
    const time = timestamp
      ? new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      : new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    addMessage({
      role: 'assistant',
      type: 'text',
      content: `Email sent successfully to ${toEmail} at ${time}.`,
    });
  };

  // Handle file selection from action buttons
  const handleFileSelect = (event) => {
    const file = event.target.files?.[0];
    if (file) {
      handleUploadDocument(file);
    }
    // Reset input so same file can be selected again
    event.target.value = '';
  };

  return (
    <div className="flex flex-col h-[700px] bg-[#0a0a0f] border border-white/10 rounded-2xl shadow-2xl overflow-hidden backdrop-blur-xl relative">
      {/* Noise Texture */}
      <div
        className="absolute inset-0 opacity-[0.015] pointer-events-none"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 400 400' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`,
        }}
      />

      {/* Gradient Glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-96 h-96 bg-gradient-to-br from-orange-500/10 to-pink-500/10 rounded-full blur-[100px] pointer-events-none" />

      {/* Hidden file input for action buttons */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileSelect}
        accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
        className="hidden"
      />

      {/* Chat Header */}
      <div className="relative z-10 bg-white/5 backdrop-blur-xl border-b border-white/10 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-500 to-pink-500 flex items-center justify-center font-bold text-lg text-white shadow-lg shadow-orange-500/20">
              S
            </div>
            <div>
              <h2 className="text-lg font-bold text-white" style={{ fontFamily: 'Space Grotesk, system-ui, sans-serif' }}>
                Saathi <span className="text-orange-400">(साथी)</span>
              </h2>
              <p className="text-xs text-gray-400">MoMSME Dispute Resolution Assistant</p>
            </div>
          </div>

          {/* Language Selector */}
          <div className="flex gap-2">
            <button
              onClick={() => setSelectedLanguage('en')}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-300 ${
                selectedLanguage === 'en'
                  ? 'bg-gradient-to-r from-orange-500 to-pink-500 text-white shadow-lg shadow-orange-500/20'
                  : 'bg-white/5 text-gray-300 hover:bg-white/10 border border-white/10'
              }`}
            >
              EN
            </button>
            <button
              onClick={() => setSelectedLanguage('hi')}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-300 ${
                selectedLanguage === 'hi'
                  ? 'bg-gradient-to-r from-orange-500 to-pink-500 text-white shadow-lg shadow-orange-500/20'
                  : 'bg-white/5 text-gray-300 hover:bg-white/10 border border-white/10'
              }`}
            >
              हि
            </button>
            <button
              onClick={() => setSelectedLanguage('kn')}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-300 ${
                selectedLanguage === 'kn'
                  ? 'bg-gradient-to-r from-orange-500 to-pink-500 text-white shadow-lg shadow-orange-500/20'
                  : 'bg-white/5 text-gray-300 hover:bg-white/10 border border-white/10'
              }`}
            >
              ಕ
            </button>
          </div>
        </div>
      </div>

      {/* Claim Progress Bar */}
      <ClaimProgress completeness={completeness} />

      {/* Messages Area */}
      <div className="relative z-10 flex-1 overflow-y-auto px-6 py-6 space-y-4">
        {messages.map((message) => (
          <ChatMessage
            key={message.id}
            message={message}
            conversationId={conversationId}
            onEmailSent={handleEmailSent}
          />
        ))}

        {/* Only show bouncing dots loader if loading but no streaming message exists */}
        {isLoading && !messages.some(msg => msg.isStreaming) && (
          <div className="flex gap-3 justify-start">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-orange-500 to-pink-500 flex items-center justify-center flex-shrink-0 shadow-lg shadow-orange-500/20">
              <Loader2 className="w-5 h-5 text-white animate-spin" />
            </div>
            <div className="bg-white/5 backdrop-blur-lg border border-white/10 rounded-2xl px-5 py-3">
              <div className="flex gap-2">
                <div className="w-2 h-2 bg-orange-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-pink-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="relative z-10">
        <ChatInput
          onSendMessage={handleSendTextMessage}
          onSendVoice={handleSendVoiceMessage}
          onUploadDocument={handleUploadDocument}
          disabled={isLoading}
        />
      </div>
    </div>
  );
}
