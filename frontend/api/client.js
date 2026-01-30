import axios from 'axios';
import { Platform } from 'react-native';

// Change this to your machine's IP address if running on physical device
const BASE_URL = Platform.OS === 'android'
  ? 'http://10.0.2.2:8091/api/v1'
  : 'http://localhost:8091/api/v1';

const api = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30s timeout for LLM responses
});

export const uploadDocument = async (file) => {
  const formData = new FormData();
  
  if (Platform.OS === 'web') {
    // On web, expo-document-picker returns a 'file' object which is a standard File/Blob
    const fileToUpload = file.file || file;
    formData.append('file', fileToUpload, file.name || 'document.pdf');
  } else {
    // On native, we use the {uri, name, type} object
    formData.append('file', {
      uri: file.uri,
      name: file.name,
      type: file.mimeType || 'application/pdf',
    });
  }

  try {
    const response = await api.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  } catch (error) {
    console.error('Upload error:', error);
    throw error;
  }
};

export const chatWithBot = async (query) => {
  try {
    const response = await api.post(`/chat?query=${encodeURIComponent(query)}`);
    return response.data;
  } catch (error) {
    console.error('Chat error:', error);
    throw error;
  }
};

export const listDocuments = async () => {
  try {
    const response = await api.get('/documents');
    return response.data;
  } catch (error) {
    console.error('List docs error:', error);
    throw error;
  }
};

export const getDashboardStats = async () => {
  try {
    const response = await api.get('/dashboard/stats');
    return response.data;
  } catch (error) {
    console.error('Dashboard stats error:', error);
    throw error;
  }
};

export const getDocument = async (docId) => {
  try {
    const response = await api.get(`/documents/${docId}`);
    return response.data;
  } catch (error) {
    console.error('Get document error:', error);
    throw error;
  }
};
