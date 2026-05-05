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

export async function fetchDeadlines(folderId) {
  const token = getToken();
  if (!token) return null;

  try {
    const params = { token };
    if (folderId) params.folder_id = folderId;
    const response = await api.get('/deadlines', { params });
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

export async function createDeadline(deadline, folderId) {
  const token = getToken();
  if (!token) return null;

  try {
    const body = folderId ? { ...deadline, folder_id: folderId } : deadline;
    const response = await api.post('/deadlines', body, { params: { token } });
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

export async function deleteAllDeadlinesApi(folderId) {
  const token = getToken();
  if (!token) return false;

  try {
    const params = { token };
    if (folderId) params.folder_id = folderId;
    await api.delete('/deadlines', { params });
    return true;
  } catch (error) {
    console.error('Failed to delete all deadlines:', error);
    return false;
  }
}

// Folders API
export async function fetchFolders() {
  const token = getToken();
  if (!token) return null;
  try {
    const response = await api.get('/folders', { params: { token } });
    return response.data;
  } catch (error) {
    console.error('Failed to fetch folders:', error);
    return null;
  }
}

export async function createFolderApi(data) {
  const token = getToken();
  if (!token) return null;
  try {
    const response = await api.post('/folders', data, { params: { token } });
    return response.data;
  } catch (error) {
    console.error('Failed to create folder:', error);
    return null;
  }
}

export async function updateFolderApi(folderId, data) {
  const token = getToken();
  if (!token) return null;
  try {
    const response = await api.put(`/folders/${folderId}`, data, { params: { token } });
    return response.data;
  } catch (error) {
    console.error('Failed to update folder:', error);
    return null;
  }
}

export async function deleteFolderApi(folderId) {
  const token = getToken();
  if (!token) return false;
  try {
    await api.delete(`/folders/${folderId}`, { params: { token } });
    return true;
  } catch (error) {
    console.error('Failed to delete folder:', error);
    return false;
  }
}

// Notes API
export async function fetchNotes(folderId) {
  const token = getToken();
  if (!token) return null;
  try {
    const response = await api.get('/notes', { params: { token, folder_id: folderId } });
    return response.data;
  } catch (error) {
    console.error('Failed to fetch notes:', error);
    return null;
  }
}

export async function createNoteApi(data) {
  const token = getToken();
  if (!token) return null;
  try {
    const response = await api.post('/notes', data, { params: { token } });
    return response.data;
  } catch (error) {
    console.error('Failed to create note:', error);
    return null;
  }
}

export async function updateNoteApi(noteId, data) {
  const token = getToken();
  if (!token) return null;
  try {
    const response = await api.put(`/notes/${noteId}`, data, { params: { token } });
    return response.data;
  } catch (error) {
    console.error('Failed to update note:', error);
    return null;
  }
}

export async function deleteNoteApi(noteId) {
  const token = getToken();
  if (!token) return false;
  try {
    await api.delete(`/notes/${noteId}`, { params: { token } });
    return true;
  } catch (error) {
    console.error('Failed to delete note:', error);
    return false;
  }
}

export async function reorderNotesApi(items) {
  const token = getToken();
  if (!token) return false;
  try {
    await api.put('/notes/reorder', items, { params: { token } });
    return true;
  } catch (error) {
    console.error('Failed to reorder notes:', error);
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
