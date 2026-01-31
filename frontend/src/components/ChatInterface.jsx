import { useState, useRef, useEffect } from 'react';
import { Loader2 } from 'lucide-react';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import { sendChatMessage, transcribeAudio, uploadChatDocument } from '../services/api';

export default function ChatInterface() {
  const [messages, setMessages] = useState([
    {
      id: 1,
      role: 'assistant',
      type: 'text',
      content: "Hi! I'm here to help you file an MSME payment dispute. Tell me about your issue - you can type or use voice to speak in any language.",
      timestamp: new Date().toISOString(),
    }
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

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
      const transcriptionResult = await transcribeAudio(audioBlob, 'en', conversationId);
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

  const getAIResponse = async (userMessage, messageType, documentData = null) => {
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

      // Call chat API
      const response = await sendChatMessage({
        conversation_id: conversationId,
        messages: conversationHistory,
        message_type: messageType
      });

      // Add AI response
      addMessage({
        role: 'assistant',
        type: 'text',
        content: response.response,
        actions: response.actions || [],
      });

    } catch (error) {
      console.error('Error getting AI response:', error);
      addMessage({
        role: 'assistant',
        type: 'text',
        content: 'Sorry, I encountered an error. Please try again.',
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[600px] bg-white rounded-xl shadow-lg overflow-hidden">
      {/* Chat Header */}
      <div className="bg-blue-500 text-white px-6 py-4">
        <h2 className="text-xl font-semibold">MSME Dispute Assistant</h2>
        <p className="text-sm text-blue-100 mt-1">Powered by AI - Ask me anything in any language</p>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-6 py-4 bg-gray-50">
        {messages.map((message) => (
          <ChatMessage key={message.id} message={message} />
        ))}

        {isLoading && (
          <div className="flex gap-3 justify-start mb-4">
            <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center flex-shrink-0">
              <Loader2 className="w-5 h-5 text-white animate-spin" />
            </div>
            <div className="bg-gray-100 rounded-lg px-4 py-3">
              <div className="flex gap-2">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <ChatInput
        onSendMessage={handleSendTextMessage}
        onSendVoice={handleSendVoiceMessage}
        onUploadDocument={handleUploadDocument}
        disabled={isLoading}
      />
    </div>
  );
}
