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

export const fetchGameDetail = async (appId) => {
  const response = await api.get(`/games/${appId}`);
  return response.data;
};

export const addJournalEntry = async (appId, text) => {
  const response = await api.post(`/games/${appId}/journal`, { text });
  return response.data;
};

export const updateJournalEntry = async (appId, entryId, text) => {
  const response = await api.put(`/games/${appId}/journal/${entryId}`, { text });
  return response.data;
};

export const deleteJournalEntry = async (appId, entryId) => {
  const response = await api.delete(`/games/${appId}/journal/${entryId}`);
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

export const bulkUpdateGames = async (payload) => {
  const response = await api.put('/games/bulk', payload);
  return response.data;
};

export const getRecommendation = async (params = {}) => {
  const response = await api.get('/recommend', { params });
  return response.data;
};

export const fetchContinuation = async () => {
  const response = await api.get('/recommend/continuation');
  return response.data;
};

export const fetchResume = async () => {
  const response = await api.get('/recommend/resume');
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

export const previewExternalImport = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/import/external/preview', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const importExternalLibrary = async (file, replaceMetadata) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('replace_metadata', replaceMetadata ? 'true' : 'false');
  const response = await api.post('/import/external', formData, {
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

export const fetchAutomationStatus = async () => {
  const response = await api.get('/stats/automation');
  return response.data;
};

export const postRecommendationDecision = async (payload) => {
  const response = await api.post('/recommendations/decisions', payload);
  return response.data;
};

export const fetchProfiles = async () => {
  const response = await api.get('/profiles');
  return response.data;
};

export const createProfile = async (payload) => {
  const response = await api.post('/profiles', payload);
  return response.data;
};

export const deleteProfile = async (id) => {
  const response = await api.delete(`/profiles/${id}`);
  return response.data;
};

export const fetchPendingOutcome = async () => {
  const response = await api.get('/session-outcomes/pending');
  return response.data;
};

export const postSessionOutcome = async (payload) => {
  const response = await api.post('/session-outcomes', payload);
  return response.data;
};

export const fetchArchaeology = async () => {
  const response = await api.get('/archaeology');
  return response.data;
};

export const dismissArchaeology = async (gameId, action) => {
  const response = await api.post(`/archaeology/${gameId}/dismiss`, { action });
  return response.data;
};

export default api;
