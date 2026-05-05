import { useState, useEffect, useCallback } from 'react';
import { fetchFolders, createFolderApi, updateFolderApi, deleteFolderApi, hasToken } from '../services/api';

function getFolderIdFromUrl() {
  const params = new URLSearchParams(window.location.search);
  return params.get('folder');
}

function setFolderIdInUrl(folderId) {
  const params = new URLSearchParams(window.location.search);
  if (folderId) {
    params.set('folder', folderId);
  } else {
    params.delete('folder');
  }
  const newUrl = `${window.location.pathname}?${params.toString()}`;
  window.history.replaceState(null, '', newUrl);
}

export function useFolders() {
  const [folders, setFolders] = useState([]);
  const [activeFolderId, setActiveFolderId] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!hasToken()) {
      setLoading(false);
      return;
    }
    fetchFolders().then((data) => {
      if (!data) { setLoading(false); return; }
      setFolders(data);

      const urlFolderId = getFolderIdFromUrl();
      const validFolder = urlFolderId && data.find(f => f.id === urlFolderId);
      if (validFolder) {
        setActiveFolderId(urlFolderId);
      } else {
        const defaultFolder = data.find(f => f.is_default) || data[0];
        if (defaultFolder) {
          setActiveFolderId(defaultFolder.id);
          setFolderIdInUrl(defaultFolder.id);
        }
      }
      setLoading(false);
    });
  }, []);

  const switchFolder = useCallback((folderId) => {
    setActiveFolderId(folderId);
    setFolderIdInUrl(folderId);
  }, []);

  const createFolder = useCallback(async (name, type) => {
    const folder = await createFolderApi({ name, type });
    if (folder) {
      setFolders(prev => [...prev, folder]);
      switchFolder(folder.id);
    }
    return folder;
  }, [switchFolder]);

  const renameFolder = useCallback(async (folderId, name) => {
    const updated = await updateFolderApi(folderId, { name });
    if (updated) {
      setFolders(prev => prev.map(f => f.id === folderId ? updated : f));
    }
    return updated;
  }, []);

  const deleteFolder = useCallback(async (folderId) => {
    const ok = await deleteFolderApi(folderId);
    if (ok) {
      setFolders(prev => {
        const next = prev.filter(f => f.id !== folderId);
        if (activeFolderId === folderId && next.length > 0) {
          const fallback = next.find(f => f.is_default) || next[0];
          setActiveFolderId(fallback.id);
          setFolderIdInUrl(fallback.id);
        }
        return next;
      });
    }
    return ok;
  }, [activeFolderId]);

  const activeFolder = folders.find(f => f.id === activeFolderId) || null;

  return { folders, activeFolderId, activeFolder, loading, switchFolder, createFolder, renameFolder, deleteFolder };
}
