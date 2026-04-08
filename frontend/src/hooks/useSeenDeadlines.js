import { useState, useCallback, useEffect, useRef } from 'react';

const STORAGE_KEY = 'seen-deadline-ids';

export function useSeenDeadlines() {
  const isFirstLoad = useRef(!localStorage.getItem(STORAGE_KEY));
  const [seenIds, setSeenIds] = useState(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored ? new Set(JSON.parse(stored)) : new Set();
    } catch {
      return new Set();
    }
  });

  const saveTimer = useRef(null);
  useEffect(() => {
    clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => {
      localStorage.setItem(STORAGE_KEY, JSON.stringify([...seenIds]));
    }, 300);
    return () => clearTimeout(saveTimer.current);
  }, [seenIds]);

  const isNew = useCallback((id) => !seenIds.has(id), [seenIds]);

  const markSeen = useCallback((id) => {
    setSeenIds((prev) => {
      if (prev.has(id)) return prev;
      const next = new Set(prev);
      next.add(id);
      return next;
    });
  }, []);

  const initializeWithExisting = useCallback((ids) => {
    if (!isFirstLoad.current) return;
    isFirstLoad.current = false;
    setSeenIds(new Set(ids));
  }, []);

  return { isNew, markSeen, initializeWithExisting };
}
