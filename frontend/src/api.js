import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
});

export const fetchGames = async (params = {}) => {
  const response = await api.get('/games', { params });
  return response.data;
};

export const updateGame = async (appId, updates) => {
  const response = await api.put(`/games/${appId}`, updates);
  return response.data;
};

export const getRecommendation = async (params = {}) => {
  const response = await api.get('/recommend', { params });
  return response.data;
};

export const uploadLibrary = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const autoTagLibrary = async () => {
  const response = await api.post('/games/auto-tag');
  return response.data;
};

export default api;
