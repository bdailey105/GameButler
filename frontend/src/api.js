import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
});

export const fetchGames = async (params = {}) => {
  const response = await api.get('/games', { params });
  return response.data;
};

export const addGame = async (payload) => {
  const response = await api.post('/games', payload);
  return response.data;
};

export const updateGame = async (appId, updates) => {
  const response = await api.put(`/games/${appId}`, updates);
  return response.data;
};

export const deleteGame = async (appId) => {
  const response = await api.delete(`/games/${appId}`);
  return response.data;
};

export const reorderQueue = async (appIds) => {
  const response = await api.put('/games/queue', { app_ids: appIds });
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

export const previewLibraryUpload = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/upload/preview', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const autoTagLibrary = async () => {
  const response = await api.post('/games/auto-tag');
  return response.data;
};

export const enrichLibrary = async () => {
  const response = await api.post('/games/enrich');
  return response.data;
};

export const fetchEnrichmentJob = async (jobId) => {
  const response = await api.get(`/games/enrich/jobs/${jobId}`);
  return response.data;
};

export const fetchCurrentEnrichmentJob = async () => {
  const response = await api.get('/games/enrich/jobs/current');
  return response.data;
};

export const syncSteamLibrary = async () => {
  const response = await api.post('/sync/steam');
  return response.data;
};

export const fetchActivity = async () => {
  const response = await api.get('/stats/activity');
  return response.data;
};

export default api;
