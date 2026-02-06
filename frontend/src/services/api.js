import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
});

export const transcribeAudio = async (audioBlob, language = 'en', conversationId = null) => {
  const formData = new FormData();
  formData.append('file', audioBlob, 'recording.webm');
  if (conversationId) formData.append('conversation_id', conversationId);

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
