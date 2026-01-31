import { useState, useRef, useEffect } from 'react';
import { Mic, Square, Loader2, Play, Pause, Send } from 'lucide-react';
import { transcribeAudio } from '../services/api';

export default function VoiceRecorder({ onTranscription }) {
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [audioBlob, setAudioBlob] = useState(null);
  const [audioURL, setAudioURL] = useState(null);
  const [transcription, setTranscription] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);

  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);
  const audioRef = useRef(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
      if (audioURL) {
        URL.revokeObjectURL(audioURL);
      }
    };
  }, [audioURL]);

  const startRecording = async () => {
    try {
      setError(null);
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
        setAudioBlob(blob);
        const url = URL.createObjectURL(blob);
        setAudioURL(url);
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);

      // Start timer
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);

    } catch (err) {
      console.error('Error accessing microphone:', err);
      setError('Microphone access denied. Please allow microphone permissions.');
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

  const togglePlayPause = () => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause();
      } else {
        audioRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const handleSubmit = async () => {
    if (!audioBlob) return;

    setIsLoading(true);
    setError(null);

    try {
      const result = await transcribeAudio(audioBlob);
      setTranscription(result.text);
      if (onTranscription) {
        onTranscription(result.text);
      }
    } catch (err) {
      console.error('Transcription error:', err);
      setError(err.response?.data?.detail || 'Failed to transcribe audio. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const resetRecording = () => {
    setAudioBlob(null);
    setAudioURL(null);
    setRecordingTime(0);
    setTranscription(null);
    setError(null);
    setIsPlaying(false);
    if (audioURL) {
      URL.revokeObjectURL(audioURL);
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="w-full max-w-2xl mx-auto p-6 bg-white rounded-xl shadow-lg">
      <div className="space-y-6">
        {/* Recording Controls */}
        {!audioBlob && (
          <div className="flex flex-col items-center space-y-4">
            {isRecording ? (
              <>
                <div className="relative">
                  <button
                    onClick={stopRecording}
                    className="w-20 h-20 bg-red-500 hover:bg-red-600 text-white rounded-full flex items-center justify-center shadow-lg transition-all transform hover:scale-105"
                  >
                    <Square className="w-8 h-8" fill="currentColor" />
                  </button>
                  <div className="absolute inset-0 rounded-full bg-red-500 animate-ping opacity-75 pointer-events-none"></div>
                </div>
                <div className="text-2xl font-mono font-bold text-gray-700">
                  {formatTime(recordingTime)}
                </div>
                <p className="text-gray-600">Recording... Click to stop</p>
              </>
            ) : (
              <>
                <button
                  onClick={startRecording}
                  className="w-20 h-20 bg-blue-500 hover:bg-blue-600 text-white rounded-full flex items-center justify-center shadow-lg transition-all transform hover:scale-105"
                >
                  <Mic className="w-8 h-8" />
                </button>
                <p className="text-gray-600">Click to start recording</p>
              </>
            )}
          </div>
        )}

        {/* Audio Preview */}
        {audioBlob && !transcription && (
          <div className="space-y-4">
            <div className="bg-gray-50 rounded-lg p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700">
                  Recording: {formatTime(recordingTime)}
                </span>
                <button
                  onClick={resetRecording}
                  className="text-sm text-blue-600 hover:text-blue-700"
                >
                  Record Again
                </button>
              </div>

              <div className="flex items-center space-x-4">
                <button
                  onClick={togglePlayPause}
                  className="w-12 h-12 bg-gray-200 hover:bg-gray-300 rounded-full flex items-center justify-center transition-colors"
                >
                  {isPlaying ? (
                    <Pause className="w-5 h-5 text-gray-700" />
                  ) : (
                    <Play className="w-5 h-5 text-gray-700 ml-1" />
                  )}
                </button>
                <div className="flex-1">
                  <div className="h-2 bg-gray-300 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-500 w-0"></div>
                  </div>
                </div>
              </div>

              <audio
                ref={audioRef}
                src={audioURL}
                onEnded={() => setIsPlaying(false)}
                className="hidden"
              />
            </div>

            <button
              onClick={handleSubmit}
              disabled={isLoading}
              className="w-full bg-blue-500 hover:bg-blue-600 disabled:bg-gray-400 text-white font-semibold py-3 px-6 rounded-lg flex items-center justify-center space-x-2 transition-colors"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Transcribing...</span>
                </>
              ) : (
                <>
                  <Send className="w-5 h-5" />
                  <span>Submit for Transcription</span>
                </>
              )}
            </button>
          </div>
        )}

        {/* Transcription Result */}
        {transcription && (
          <div className="space-y-4">
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-green-800 mb-2">
                Transcription
              </h3>
              <p className="text-gray-800 whitespace-pre-wrap">{transcription}</p>
            </div>
            <button
              onClick={resetRecording}
              className="w-full bg-gray-500 hover:bg-gray-600 text-white font-semibold py-3 px-6 rounded-lg transition-colors"
            >
              Record Another
            </button>
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800 text-sm">{error}</p>
          </div>
        )}
      </div>
    </div>
  );
}
