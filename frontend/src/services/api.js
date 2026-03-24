import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

const api = axios.create({
  baseURL: `${BACKEND_URL}/api`,
  timeout: 10000,
});

function getToken() {
  const params = new URLSearchParams(window.location.search);
  const urlToken = params.get('token');
  if (urlToken) {
    localStorage.setItem('dashboard_token', urlToken);
    return urlToken;
  }
  return localStorage.getItem('dashboard_token');
}

export async function fetchDeadlines() {
  const token = getToken();
  if (!token) return null;

  try {
    const response = await api.get('/deadlines', { params: { token } });
    return response.data;
  } catch (error) {
    if (error.response?.status === 401) {
      localStorage.removeItem('dashboard_token');
    }
    console.error('Failed to fetch deadlines:', error);
    return null;
  }
}

export async function createDeadline(deadline) {
  const token = getToken();
  if (!token) return null;

  try {
    const response = await api.post('/deadlines', deadline, { params: { token } });
    return response.data;
  } catch (error) {
    console.error('Failed to create deadline:', error);
    return null;
  }
}

export async function updateDeadline(deadlineId, data) {
  const token = getToken();
  if (!token) return null;

  try {
    const response = await api.put(`/deadlines/${deadlineId}`, data, { params: { token } });
    return response.data;
  } catch (error) {
    console.error('Failed to update deadline:', error);
    return null;
  }
}

export async function deleteDeadlineApi(deadlineId) {
  const token = getToken();
  if (!token) return false;

  try {
    await api.delete(`/deadlines/${deadlineId}`, { params: { token } });
    return true;
  } catch (error) {
    console.error('Failed to delete deadline:', error);
    return false;
  }
}

export function hasToken() {
  return !!getToken();
}
