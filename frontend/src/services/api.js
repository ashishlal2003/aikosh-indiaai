import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
});

export const transcribeAudio = async (audioBlob, language = 'en', conversationId = null) => {
  const formData = new FormData();
  formData.append('file', audioBlob, 'recording.webm');
  if (conversationId) formData.append('conversation_id', conversationId);
  if (language) formData.append('language', language);

  const response = await api.post('/api/transcribe-chat', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const sendChatMessage = async (payload) => {
  const response = await api.post('/api/chat', payload);
  return response.data;
};

export const sendChatMessageStream = async (payload, onEvent) => {
  /**
   * Stream chat response using Server-Sent Events (SSE).
   *
   * Args:
   *   payload: ChatRequest with conversation_id and messages
   *   onEvent: Callback function (eventType, data) => void
   *            eventType can be: 'tool_start', 'tool_end', 'message', 'done', 'error'
   *
   * Returns:
   *   Promise that resolves when stream completes
   */
  const baseURL = import.meta.env.VITE_API_URL;
  const response = await fetch(`${baseURL}/api/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // Process complete SSE messages
    const lines = buffer.split('\n\n');
    buffer = lines.pop() || ''; // Keep incomplete message in buffer

    for (const line of lines) {
      if (!line.trim()) continue;

      // Parse SSE format: "event: xxx\ndata: {...}"
      const eventMatch = line.match(/event: (\w+)\ndata: (.+)/);
      if (eventMatch) {
        const [, eventType, dataStr] = eventMatch;
        try {
          const data = JSON.parse(dataStr);
          onEvent(eventType, data);
        } catch (e) {
          console.error('Failed to parse SSE data:', dataStr, e);
        }
      }
    }
  }
};

export const sendEmail = async (conversationId, emailData) => {
  const response = await api.post('/api/chat/send-email', {
    conversation_id: conversationId,
    to_email: emailData.to_email,
    subject: emailData.subject,
    body_html: emailData.body_html,
  });
  return response.data;
};

export const uploadChatDocument = async (file, conversationId) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('conversation_id', conversationId);

  const response = await api.post('/api/chat/upload-document', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export default api;
