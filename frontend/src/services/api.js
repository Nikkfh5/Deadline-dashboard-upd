import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

const api = axios.create({
  baseURL: `${BACKEND_URL}/api`,
  timeout: 10000,
});

// Session-scoped token: pinned per tab so multiple users
// in the same browser don't overwrite each other via localStorage.
let sessionToken = null;

function getToken() {
  if (sessionToken) return sessionToken;

  const params = new URLSearchParams(window.location.search);
  const urlToken = params.get('token');
  if (urlToken) {
    // If token changed, clear cached deadlines so stale data from
    // another account doesn't leak into this session.
    const prev = localStorage.getItem('dashboard_token');
    if (prev && prev !== urlToken) {
      localStorage.removeItem('deadlines');
    }
    sessionToken = urlToken;
    localStorage.setItem('dashboard_token', urlToken);
    return sessionToken;
  }

  sessionToken = localStorage.getItem('dashboard_token');
  return sessionToken;
}

export async function fetchDeadlines() {
  const token = getToken();
  if (!token) return null;

  try {
    const response = await api.get('/deadlines', { params: { token } });
    return response.data;
  } catch (error) {
    if (error.response?.status === 401) {
      sessionToken = null;
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
    await api.delete(`/deadlines/${deadlineId}`, { params: { token, complete: false } });
    return true;
  } catch (error) {
    console.error('Failed to delete deadline:', error);
    return false;
  }
}

export async function completeDeadlineApi(deadlineId) {
  const token = getToken();
  if (!token) return false;

  try {
    await api.delete(`/deadlines/${deadlineId}`, { params: { token, complete: true } });
    return true;
  } catch (error) {
    console.error('Failed to complete deadline:', error);
    return false;
  }
}

export async function fetchStats() {
  const token = getToken();
  if (!token) return null;

  try {
    const response = await api.get('/stats', { params: { token } });
    return response.data;
  } catch (error) {
    console.error('Failed to fetch stats:', error);
    return null;
  }
}

export function hasToken() {
  return !!getToken();
}
