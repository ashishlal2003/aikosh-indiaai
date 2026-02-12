import { useState, useRef, useEffect } from 'react';
import { Send, Mic, Square, Paperclip, Loader2 } from 'lucide-react';

export default function ChatInput({ onSendMessage, onSendVoice, onUploadDocument, disabled }) {
  const [message, setMessage] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [isUploading, setIsUploading] = useState(false);

  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);
  const fileInputRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px';
    }
  }, [message]);

  const handleSend = () => {
    if (message.trim() && !disabled) {
      onSendMessage(message.trim());
      setMessage('');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm',
      });

      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        const url = URL.createObjectURL(blob);
        onSendVoice(blob, url);
        stream.getTracks().forEach(track => track.stop());
        setRecordingTime(0);
      };

      mediaRecorder.start();
      setIsRecording(true);

      // Start timer
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);

    } catch (err) {
      console.error('Error accessing microphone:', err);
      alert('Microphone access denied. Please allow microphone permissions.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    }
  };

  const handleFileSelect = async (e) => {
    const file = e.target.files[0];
    if (file && !disabled) {
      setIsUploading(true);
      try {
        await onUploadDocument(file);
      } catch (error) {
        console.error('Error uploading file:', error);
      } finally {
        setIsUploading(false);
        e.target.value = '';
      }
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="border-t border-white/10 bg-white/5 backdrop-blur-xl p-4">
      {isRecording && (
        <div className="mb-3 flex items-center justify-between bg-red-500/10 border border-red-500/20 rounded-xl p-3 backdrop-blur-lg">
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse shadow-lg shadow-red-500/50"></div>
            <span className="text-sm text-gray-200">Recording...</span>
            <span className="text-sm font-mono font-bold text-white">
              {formatTime(recordingTime)}
            </span>
          </div>
          <button
            onClick={stopRecording}
            className="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-lg flex items-center gap-2 transition-all duration-300 shadow-lg shadow-red-500/20"
          >
            <Square className="w-4 h-4" fill="currentColor" />
            <span>Stop</span>
          </button>
        </div>
      )}

      <div className="flex items-end gap-2">
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileSelect}
          className="hidden"
          accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
        />

        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled || isRecording || isUploading}
          className="p-3 text-gray-400 hover:text-white hover:bg-white/10 rounded-xl transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed border border-white/10"
          title="Upload document"
        >
          {isUploading ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <Paperclip className="w-5 h-5" />
          )}
        </button>

        <div className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 backdrop-blur-lg">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message or use voice..."
            disabled={disabled || isRecording}
            className="w-full bg-transparent border-none outline-none resize-none max-h-32 disabled:opacity-50 text-white placeholder-gray-400"
            rows={1}
          />
        </div>

        {message.trim() ? (
          <button
            onClick={handleSend}
            disabled={disabled || isRecording}
            className="p-3 bg-gradient-to-r from-orange-500 to-pink-500 hover:from-orange-600 hover:to-pink-600 text-white rounded-xl transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-orange-500/20"
            title="Send message"
          >
            <Send className="w-5 h-5" />
          </button>
        ) : (
          <button
            onClick={isRecording ? stopRecording : startRecording}
            disabled={disabled}
            className={`p-3 rounded-xl transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg ${
              isRecording
                ? 'bg-red-500 hover:bg-red-600 text-white shadow-red-500/20'
                : 'bg-gradient-to-r from-orange-500 to-pink-500 hover:from-orange-600 hover:to-pink-600 text-white shadow-orange-500/20'
            }`}
            title={isRecording ? 'Stop recording' : 'Start voice recording'}
          >
            {isRecording ? (
              <Square className="w-5 h-5" fill="currentColor" />
            ) : (
              <Mic className="w-5 h-5" />
            )}
          </button>
        )}
      </div>
    </div>
  );
}
