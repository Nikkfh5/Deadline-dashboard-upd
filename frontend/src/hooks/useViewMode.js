import { useState, useCallback, useEffect } from 'react';

function storageKey(folderId) {
  return `view-mode-${folderId}`;
}

function positionsKey(folderId) {
  return `canvas-positions-${folderId}`;
}

export function useViewMode(folderId) {
  const [viewMode, setViewModeState] = useState('list');

  useEffect(() => {
    if (!folderId) return;
    const saved = localStorage.getItem(storageKey(folderId));
    setViewModeState(saved === 'canvas' ? 'canvas' : 'list');
  }, [folderId]);

  const setViewMode = useCallback((mode) => {
    setViewModeState(mode);
    if (folderId) localStorage.setItem(storageKey(folderId), mode);
  }, [folderId]);

  const getPositions = useCallback(() => {
    if (!folderId) return {};
    try {
      return JSON.parse(localStorage.getItem(positionsKey(folderId)) || '{}');
    } catch {
      return {};
    }
  }, [folderId]);

  const savePosition = useCallback((cardId, x, y) => {
    if (!folderId) return;
    const positions = getPositions();
    positions[cardId] = { x, y };
    localStorage.setItem(positionsKey(folderId), JSON.stringify(positions));
  }, [folderId, getPositions]);

  const resetPositions = useCallback(() => {
    if (folderId) localStorage.removeItem(positionsKey(folderId));
  }, [folderId]);

  return { viewMode, setViewMode, getPositions, savePosition, resetPositions };
}
