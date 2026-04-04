import { useState, useCallback, useEffect, useRef } from 'react';

const STORAGE_KEY = 'manual-plan';

export function useManualPlan() {
  const [manualPlan, setManualPlan] = useState(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored ? JSON.parse(stored) : {};
    } catch {
      return {};
    }
  });

  const saveTimer = useRef(null);
  useEffect(() => {
    clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(manualPlan));
    }, 300);
    return () => clearTimeout(saveTimer.current);
  }, [manualPlan]);

  const toggleDay = useCallback((deadlineId, dateKey) => {
    setManualPlan((prev) => {
      const entry = prev[deadlineId] || { colorIndex: 0, days: [] };
      const days = entry.days.includes(dateKey)
        ? entry.days.filter((d) => d !== dateKey)
        : [...entry.days, dateKey];
      return { ...prev, [deadlineId]: { ...entry, days } };
    });
  }, []);

  const setColor = useCallback((deadlineId, colorIndex) => {
    setManualPlan((prev) => {
      const entry = prev[deadlineId] || { colorIndex: 0, days: [] };
      return { ...prev, [deadlineId]: { ...entry, colorIndex } };
    });
  }, []);

  const clearDeadline = useCallback((deadlineId) => {
    setManualPlan((prev) => {
      const next = { ...prev };
      delete next[deadlineId];
      return next;
    });
  }, []);

  const hasManualDays = useCallback(
    (deadlineId) => {
      const entry = manualPlan[deadlineId];
      return entry && entry.days.length > 0;
    },
    [manualPlan]
  );

  const clearAll = useCallback(() => {
    setManualPlan({});
  }, []);

  const loadManualPlan = useCallback((plan) => {
    setManualPlan(plan || {});
  }, []);

  return { manualPlan, toggleDay, setColor, clearDeadline, clearAll, hasManualDays, loadManualPlan };
}
