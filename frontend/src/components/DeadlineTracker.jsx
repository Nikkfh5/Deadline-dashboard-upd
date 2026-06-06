import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Clock, Plus, Moon, Sun, ChevronDown, ChevronUp, Calendar as CalendarIcon, LayoutGrid, Trash2, CheckCircle2, List, TimerOff } from 'lucide-react';
import { Button } from './ui/button';
import { TooltipProvider } from './ui/tooltip';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from './ui/collapsible';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from './ui/dropdown-menu';
import { mockDeadlines } from '../mock';
import { fetchDeadlines, createDeadline, updateDeadline, deleteDeadlineApi, completeDeadlineApi, deleteAllDeadlinesApi, deleteExpiredDeadlinesApi, hasToken } from '../services/api';
import StatsPanel from './StatsPanel';
import DeadlineCard from './DeadlineCard';
import DeadlineModal from './DeadlineModal';
import DeadlineCalendar from './DeadlineCalendar';
import SnapshotManager from './SnapshotManager';
import ManualPlanningToolbar from './ManualPlanningToolbar';
import { useSnapshots } from '../hooks/useSnapshots';
import { useManualPlan } from '../hooks/useManualPlan';
import { useSeenDeadlines } from '../hooks/useSeenDeadlines';
import { useViewMode } from '../hooks/useViewMode';
import { migrateDeadline, normalizeServerDeadline } from '../lib/deadline-normalization';
import CanvasView from './CanvasView';
import FolderTabs from './FolderTabs';
import NotesView from './NotesView';

// Merge server deadlines with local-only deadlines
// Server is the source of truth — only keep local items that are very recent (< 10s old, likely just created)
const mergeDeadlines = (serverList, localList) => {
  const serverIds = new Set(serverList.map(d => d.id));
  const now = Date.now();
  const localOnly = localList.filter(d =>
    !serverIds.has(d.id) && !d._fromServer &&
    (now - parseInt(d.id)) < 10000 // keep only items created < 10s ago (id is Date.now())
  );
  return [...serverList, ...localOnly];
};

const DeadlineTracker = ({ foldersApi }) => {
  const folderId = foldersApi?.activeFolderId ?? null;
  const activeFolder = foldersApi?.activeFolder ?? null;
  const [deadlines, setDeadlines] = useState([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingDeadline, setEditingDeadline] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    task: '',
    dueDate: '',
    isRecurring: false,
    intervalDays: '7',
    customDays: '',
    daysNeeded: ''
  });
  const [currentTime, setCurrentTime] = useState(new Date());
  const [isTemporaryCollapsed, setIsTemporaryCollapsed] = useState(true);
  const [isCalendarCollapsed, setIsCalendarCollapsed] = useState(true);
  const [isPlanningMode, setIsPlanningMode] = useState(false);
  const [planningSubMode, setPlanningSubMode] = useState('auto');
  const [manualActiveDeadlineId, setManualActiveDeadlineId] = useState(null);
  const recentlyDeletedRef = useRef(new Set());
  const { snapshots, saveSnapshot, deleteSnapshot, exportSnapshotAsText } = useSnapshots();
  const { manualPlan, toggleDay, setColor, clearDeadline, clearAll: clearAllManual, loadManualPlan } = useManualPlan();
  const { isNew, markSeen, initializeWithExisting } = useSeenDeadlines();
  const handleDayClick = useCallback((dateKey) => {
    if (manualActiveDeadlineId) {
      toggleDay(manualActiveDeadlineId, dateKey);
    }
  }, [manualActiveDeadlineId, toggleDay]);

  const [statsKey, setStatsKey] = useState(0);
  const refreshStats = () => setStatsKey(k => k + 1);
  const [isDeleteMenuOpen, setIsDeleteMenuOpen] = useState(false);
  const { viewMode, setViewMode, getPositions, savePosition, resetPositions } = useViewMode(folderId);
  const [showTemporaryInCanvas, setShowTemporaryInCanvas] = useState(false);
  const doSyncRef = useRef(null);
  const lsKey = folderId ? `deadlines-${folderId}` : 'deadlines';
  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem('darkMode');
    if (saved !== null) return saved === 'true';
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode);
    localStorage.setItem('darkMode', darkMode);
  }, [darkMode]);

  useEffect(() => {
    // Read cache synchronously so there's no empty-screen flash when switching folders
    let cachedDeadlines = [];
    const saved = localStorage.getItem(lsKey);
    if (saved) {
      try { cachedDeadlines = JSON.parse(saved).map(migrateDeadline); } catch {}
    } else if (!folderId) {
      cachedDeadlines = mockDeadlines.map(migrateDeadline);
    }

    setDeadlines(cachedDeadlines);
    recentlyDeletedRef.current = new Set();
    setIsDeleteMenuOpen(false);
    if (cachedDeadlines.length) initializeWithExisting(cachedDeadlines.map(d => d.id));

    // Fetch from server in background
    if (hasToken()) {
      fetchDeadlines(folderId).then(serverDeadlines => {
        if (serverDeadlines === null) return;
        const normalized = serverDeadlines.map(normalizeServerDeadline);
        const merged = mergeDeadlines(normalized, cachedDeadlines);
        setDeadlines(merged);
        initializeWithExisting(merged.map(d => d.id));
        localStorage.setItem(lsKey, JSON.stringify(merged));
      });
    }
  }, [folderId]); // lsKey derived from folderId, migrateDeadline/mockDeadlines are stable

  useEffect(() => {
    // Update current time every second
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Smart sync: 10s when tab visible, 0 when hidden, instant on tab focus
  const syncIntervalRef = useRef(null);
  const doSync = async () => {
    const serverDeadlines = await fetchDeadlines(folderId);
    if (serverDeadlines !== null) {
      const deleted = recentlyDeletedRef.current;
      const normalized = serverDeadlines
        .map(normalizeServerDeadline)
        .filter(d => !deleted.has(d.id));
      setDeadlines(prev => {
        const merged = mergeDeadlines(normalized, prev);
        if (merged.length === prev.length && merged.every((d, i) => d.id === prev[i]?.id)) return prev;
        return merged;
      });
    }
  };
  // Keep ref current so the polling interval always calls the latest version
  doSyncRef.current = doSync;

  useEffect(() => {
    if (!hasToken()) return;

    const startPolling = () => {
      clearInterval(syncIntervalRef.current);
      syncIntervalRef.current = setInterval(() => doSyncRef.current?.(), 10000);
    };
    const stopPolling = () => {
      clearInterval(syncIntervalRef.current);
    };

    const onVisibility = () => {
      if (document.visibilityState === 'visible') {
        doSyncRef.current?.();
        startPolling();
      } else {
        stopPolling();
      }
    };

    document.addEventListener('visibilitychange', onVisibility);
    if (document.visibilityState === 'visible') startPolling();

    return () => {
      stopPolling();
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, []);

  const saveTimerRef = useRef(null);
  useEffect(() => {
    if (!deadlines.length) return;
    clearTimeout(saveTimerRef.current);
    saveTimerRef.current = setTimeout(() => {
      localStorage.setItem(lsKey, JSON.stringify(deadlines));
    }, 500);
    return () => clearTimeout(saveTimerRef.current);
  }, [deadlines, lsKey]);

  const calculateTimeLeft = (dueDate) => {
    // All calculations in UTC, stored timestamps are in UTC
    const now = currentTime.getTime();
    const due = new Date(dueDate).getTime();
    const diff = due - now;

    if (diff <= 0) {
      return { days: 0, hours: 0, minutes: 0, seconds: 0, isOverdue: true, totalMs: Math.abs(diff) };
    }

    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((diff % (1000 * 60)) / 1000);

    return { days, hours, minutes, seconds, isOverdue: false, totalMs: diff };
  };

  const getDeadlineMetrics = (timeLeft, deadline) => {
    if (timeLeft.isOverdue) {
      return { progressColor: 'stroke-red-500', progressPercentage: 0, isPulsing: true };
    }
    const now = currentTime.getTime();
    const startTime = deadline.isRecurring && deadline.lastStartedAt
      ? new Date(deadline.lastStartedAt).getTime()
      : new Date(deadline.createdAt).getTime();
    const due = new Date(deadline.dueDate).getTime();
    const totalDuration = due - startTime;
    const progress = totalDuration > 0 ? (now - startTime) / totalDuration : 1;

    const progressColor = progress < 0.5 ? 'stroke-green-500' : progress < 0.9 ? 'stroke-yellow-500' : 'stroke-red-500';
    const progressPercentage = Math.max(0, Math.min(100, (1 - progress) * 100));
    const isPulsing = progress >= 0.9;
    return { progressColor, progressPercentage, isPulsing };
  };

  // Helper function to format datetime for input (UTC to Moscow display)
  const formatDateTimeForInput = (utcDate) => {
    const date = new Date(utcDate);
    // Convert to Moscow timezone for display in form
    const moscowTime = new Intl.DateTimeFormat('sv-SE', {
      timeZone: 'Europe/Moscow',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    }).format(date).replace(' ', 'T');

    return moscowTime;
  };

  // Helper function to convert Moscow datetime to UTC for storage
  const moscowToUTC = (moscowDateTimeLocal) => {
    // For simplicity, treat input as local time and convert to UTC
    return new Date(moscowDateTimeLocal).toISOString();
  };

  // Function to handle recurring deadline repetition
  const handleRepeatDeadline = (deadline) => {
    const now = new Date();
    const intervalMs = deadline.intervalDays * 24 * 60 * 60 * 1000;
    const newDueDate = new Date(now.getTime() + intervalMs);

    const updatedDeadline = {
      ...deadline,
      dueDate: newDueDate.toISOString(),
      lastStartedAt: now.toISOString(),
      updatedAt: now.toISOString(),
      isMarked: false
    };

    setDeadlines(prev => prev.map(d => d.id === deadline.id ? updatedDeadline : d));

    if (hasToken()) {
      updateDeadline(deadline.id, {
        due_date: newDueDate.toISOString(),
        last_started_at: now.toISOString(),
        is_marked: false,
      }).then(refreshStats);
    }
  };

  // Filter and sort deadlines
  const getFilteredDeadlines = () => {
    const now = currentTime.getTime();

    const recurring = deadlines
      .filter(d => d.isRecurring && new Date(d.dueDate).getTime() > now)
      .sort((a, b) => new Date(a.dueDate).getTime() - new Date(b.dueDate).getTime());

    const regular = deadlines
      .filter(d => !d.isRecurring || new Date(d.dueDate).getTime() <= now)
      .sort((a, b) => new Date(a.dueDate).getTime() - new Date(b.dueDate).getTime());

    return { recurring, regular };
  };

  const openAddModal = () => {
    setEditingDeadline(null);
    // Default to today at 23:59 Moscow time
    const now = new Date();
    const moscowToday = new Intl.DateTimeFormat('sv-SE', {
      timeZone: 'Europe/Moscow',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    }).format(now);
    setFormData({
      name: '',
      task: '',
      dueDate: `${moscowToday}T23:59`,
      isRecurring: false,
      intervalDays: '7',
      customDays: '',
      daysNeeded: ''
    });
    setIsModalOpen(true);
  };

  const openEditModal = (deadline) => {
    markSeen(deadline.id);
    setEditingDeadline(deadline);
    setFormData({
      name: deadline.name,
      task: deadline.task || '',
      dueDate: formatDateTimeForInput(deadline.dueDate),
      isRecurring: deadline.isRecurring || false,
      intervalDays: deadline.intervalDays ? deadline.intervalDays.toString() : '7',
      customDays: '',
      daysNeeded: deadline.daysNeeded ? deadline.daysNeeded.toString() : ''
    });
    setIsModalOpen(true);
  };

  const handleSaveDeadline = () => {
    if (!formData.name.trim() || !formData.task.trim() || !formData.dueDate) return;

    const now = new Date();
    const utcDueDate = moscowToUTC(formData.dueDate);

    // Get the correct interval value
    const getIntervalDays = () => {
      if (formData.intervalDays === 'custom') {
        return parseInt(formData.customDays) || 7;
      }
      return parseInt(formData.intervalDays) || 7;
    };

    if (editingDeadline) {
      // Update existing deadline
      const isRecurringChanged = formData.isRecurring !== editingDeadline.isRecurring;
      const currentInterval = getIntervalDays();
      const intervalChanged = currentInterval !== (editingDeadline.intervalDays || 7);

      let newDueDate = utcDueDate;
      let newLastStartedAt = editingDeadline.lastStartedAt;

      // If editing a recurring deadline and interval changed, recalculate dueDate
      if (editingDeadline.isRecurring && formData.isRecurring && intervalChanged) {
        const lastStarted = new Date(editingDeadline.lastStartedAt || editingDeadline.createdAt);
        const intervalMs = currentInterval * 24 * 60 * 60 * 1000;
        newDueDate = new Date(lastStarted.getTime() + intervalMs).toISOString();
      }

      // If converting to recurring, set lastStartedAt to now
      if (!editingDeadline.isRecurring && formData.isRecurring) {
        newLastStartedAt = now.toISOString();
      }

      const updatedDeadline = {
        ...editingDeadline,
        name: formData.name.trim(),
        task: formData.task.trim(),
        dueDate: newDueDate,
        updatedAt: now.toISOString(),
        isRecurring: formData.isRecurring,
        intervalDays: formData.isRecurring ? currentInterval : undefined,
        lastStartedAt: newLastStartedAt,
        daysNeeded: formData.daysNeeded ? parseInt(formData.daysNeeded) : null
      };
      setDeadlines(prev => prev.map(d => d.id === editingDeadline.id ? updatedDeadline : d));
      // Sync update to backend
      if (hasToken()) {
        updateDeadline(editingDeadline.id, {
          name: updatedDeadline.name,
          task: updatedDeadline.task,
          due_date: updatedDeadline.dueDate,
          is_recurring: updatedDeadline.isRecurring,
          interval_days: updatedDeadline.intervalDays,
          last_started_at: updatedDeadline.lastStartedAt,
          days_needed: updatedDeadline.daysNeeded,
        }).then(refreshStats);
      }
    } else {
      // Add new deadline
      const deadline = {
        id: Date.now().toString(),
        name: formData.name.trim(),
        task: formData.task.trim(),
        createdAt: now.toISOString(),
        dueDate: utcDueDate,
        updatedAt: now.toISOString(),
        isRecurring: formData.isRecurring,
        intervalDays: formData.isRecurring ? getIntervalDays() : undefined,
        lastStartedAt: formData.isRecurring ? now.toISOString() : undefined,
        daysNeeded: formData.daysNeeded ? parseInt(formData.daysNeeded) : null,
        isMarked: false
      };
      setDeadlines(prev => [...prev, deadline]);
      markSeen(deadline.id);
      // Sync create to backend — replace local ID with server ID
      if (hasToken()) {
        createDeadline({
          name: deadline.name,
          task: deadline.task,
          due_date: deadline.dueDate,
          is_recurring: deadline.isRecurring,
          interval_days: deadline.intervalDays,
          last_started_at: deadline.lastStartedAt,
          days_needed: deadline.daysNeeded,
          is_marked: deadline.isMarked,
        }, folderId).then((serverDeadline) => {
          if (serverDeadline) {
            const normalized = normalizeServerDeadline(serverDeadline);
            markSeen(normalized.id);
            setDeadlines(prev => prev.map(d =>
              d.id === deadline.id ? normalized : d
            ));
          }
          refreshStats();
        });
      }
    }

    setFormData({ name: '', task: '', dueDate: '', isRecurring: false, intervalDays: '7', customDays: '', daysNeeded: '' });
    setEditingDeadline(null);
    setIsModalOpen(false);
  };

  const handleDeleteDeadline = (id) => {
    recentlyDeletedRef.current.add(id);
    setTimeout(() => recentlyDeletedRef.current.delete(id), 30000);
    setDeadlines(prev => prev.filter(d => d.id !== id));
    clearDeadline(id);
    if (manualActiveDeadlineId === id) setManualActiveDeadlineId(null);
    if (hasToken()) {
      deleteDeadlineApi(id).then(refreshStats);
    }
  };

  const handleCompleteDeadline = (id) => {
    recentlyDeletedRef.current.add(id);
    setTimeout(() => recentlyDeletedRef.current.delete(id), 30000);
    setDeadlines(prev => prev.filter(d => d.id !== id));
    if (hasToken()) {
      completeDeadlineApi(id).then(refreshStats);
    }
  };

  const isDeadlineExpired = (deadline) => new Date(deadline.dueDate).getTime() <= currentTime.getTime();

  const handleToggleMarked = (id) => {
    const current = deadlines.find(d => d.id === id);
    if (!current) return;

    const isMarked = !current.isMarked;
    const updatedAt = new Date().toISOString();
    setDeadlines(prev => prev.map(d => d.id === id ? { ...d, isMarked, updatedAt } : d));
    if (hasToken()) {
      updateDeadline(id, { is_marked: isMarked }).then(refreshStats);
    }
  };

  const handleDeleteAll = async () => {
    const allIds = deadlines.map(d => d.id);
    allIds.forEach(id => {
      recentlyDeletedRef.current.add(id);
      setTimeout(() => recentlyDeletedRef.current.delete(id), 30000);
    });
    setDeadlines([]);
    localStorage.setItem(lsKey, JSON.stringify([]));
    clearAllManual();
    setManualActiveDeadlineId(null);
    setIsDeleteMenuOpen(false);
    if (hasToken()) {
      await deleteAllDeadlinesApi(folderId);
      refreshStats();
    }
  };

  const handleDeleteExpired = async () => {
    const expiredIds = deadlines.filter(isDeadlineExpired).map(d => d.id);
    if (!expiredIds.length) return;

    expiredIds.forEach(id => {
      recentlyDeletedRef.current.add(id);
      setTimeout(() => recentlyDeletedRef.current.delete(id), 30000);
      clearDeadline(id);
    });

    setDeadlines(prev => {
      const remaining = prev.filter(d => !expiredIds.includes(d.id));
      localStorage.setItem(lsKey, JSON.stringify(remaining));
      return remaining;
    });
    if (expiredIds.includes(manualActiveDeadlineId)) setManualActiveDeadlineId(null);
    setIsDeleteMenuOpen(false);
    if (hasToken()) {
      await deleteExpiredDeadlinesApi(folderId);
      refreshStats();
    }
  };

  const daysNeededTimerRef = useRef({});
  const updateDaysNeeded = (id, value) => {
    const parsed = parseInt(value);
    const daysNeeded = isNaN(parsed) || parsed < 1 ? null : parsed;
    setDeadlines(prev => prev.map(d => d.id === id ? { ...d, daysNeeded, updatedAt: new Date().toISOString() } : d));
    if (hasToken()) {
      clearTimeout(daysNeededTimerRef.current[id]);
      daysNeededTimerRef.current[id] = setTimeout(() => {
        updateDeadline(id, { days_needed: daysNeeded });
      }, 600);
    }
  };

  // Helper function to render individual deadline card
  const renderDeadlineCard = (deadline, isRegularSection) => {
    const timeLeft = calculateTimeLeft(deadline.dueDate);
    const { progressColor, progressPercentage, isPulsing } = getDeadlineMetrics(timeLeft, deadline);

    return (
      <DeadlineCard
        key={deadline.id}
        deadline={deadline}
        timeLeft={timeLeft}
        progressColor={progressColor}
        progressPercentage={progressPercentage}
        isPulsing={isPulsing}
        onEdit={openEditModal}
        onDelete={handleDeleteDeadline}
        onComplete={handleCompleteDeadline}
        onToggleMarked={handleToggleMarked}
        onRepeat={handleRepeatDeadline}
        isRegularSection={isRegularSection}
        isPlanningMode={isPlanningMode}
        onUpdateDaysNeeded={updateDaysNeeded}
        planningSubMode={planningSubMode}
        isNew={isNew(deadline.id)}
        onMarkSeen={markSeen}
        onSelectForManual={(id) => {
          markSeen(id);
          setManualActiveDeadlineId(id === manualActiveDeadlineId ? null : id);
          if (!manualPlan[id]) {
            setColor(id, 0);
          }
        }}
        isManualSelected={manualActiveDeadlineId === deadline.id}
        manualColorIndex={manualPlan[deadline.id]?.colorIndex}
      />
    );
  };

  return (
    <TooltipProvider>
      <div className="min-h-screen bg-slate-50 dark:bg-slate-900 p-6 transition-colors">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className={`flex items-center gap-3 ${isDeleteMenuOpen ? 'mb-36 sm:mb-12' : 'mb-12'}`}>
            <div className="w-[4.5rem] shrink-0" />

            <h1 className="min-w-0 flex-1 text-center text-3xl sm:text-4xl font-bold text-slate-800 dark:text-slate-100 tracking-wide">DEADLINES</h1>

            <div className="w-[4.5rem] shrink-0 flex justify-end items-center gap-1">
              <DropdownMenu open={isDeleteMenuOpen} onOpenChange={setIsDeleteMenuOpen}>
                <div onMouseEnter={() => deadlines.length > 0 && setIsDeleteMenuOpen(true)}>
                  <DropdownMenuTrigger asChild>
                    <button
                      disabled={deadlines.length === 0}
                      title="Delete deadlines"
                      className={`
                        flex items-center justify-center w-8 h-8 rounded-lg
                        transition-all duration-200
                        ${deadlines.length === 0
                          ? 'text-slate-300 dark:text-slate-700 cursor-not-allowed'
                          : 'text-slate-400 dark:text-slate-500 hover:text-rose-500 dark:hover:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/30 cursor-pointer'
                        }
                      `}
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </DropdownMenuTrigger>
                </div>
                <DropdownMenuContent
                  align="end"
                  sideOffset={8}
                  onMouseLeave={() => setIsDeleteMenuOpen(false)}
                  className="w-44 border-slate-200 bg-white text-slate-700 shadow-lg dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                >
                  <DropdownMenuItem
                    onSelect={handleDeleteExpired}
                    disabled={!deadlines.some(isDeadlineExpired)}
                    className="cursor-pointer text-xs text-slate-600 focus:bg-slate-100 focus:text-slate-900 dark:text-slate-300 dark:focus:bg-slate-800 dark:focus:text-slate-100"
                  >
                    <TimerOff className="w-4 h-4" />
                    Delete expired
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onSelect={handleDeleteAll}
                    className="cursor-pointer text-xs text-rose-600 focus:bg-rose-50 focus:text-rose-700 dark:text-rose-400 dark:focus:bg-rose-950/40 dark:focus:text-rose-300"
                  >
                    <Trash2 className="w-4 h-4" />
                    Delete all
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setDarkMode(!darkMode)}
                className="text-slate-500 dark:text-slate-400"
              >
                {darkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
              </Button>
            </div>
          </div>

          {/* Folder Tabs */}
          {foldersApi && foldersApi.folders.length > 0 && (
            <FolderTabs
              folders={foldersApi.folders}
              activeFolderId={folderId}
              onSwitch={foldersApi.switchFolder}
              onCreate={foldersApi.createFolder}
              onRename={foldersApi.renameFolder}
              onDelete={foldersApi.deleteFolder}
            />
          )}

          {/* Ideas folder content */}
          {activeFolder?.type === 'ideas' ? (
            <NotesView folderId={folderId} />
          ) : (
          <>

          {/* Action Buttons */}
          <div className="flex justify-center gap-3 mb-8 flex-wrap">
            {/* View mode toggle */}
            <div className="flex items-center gap-1 p-1 bg-slate-100 dark:bg-slate-800 rounded-lg">
              <button
                onClick={() => setViewMode('list')}
                className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors ${
                  viewMode === 'list'
                    ? 'bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200 shadow-sm'
                    : 'text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300'
                }`}
              >
                <List className="w-3.5 h-3.5" />
                List
              </button>
              <button
                onClick={() => setViewMode('canvas')}
                className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors ${
                  viewMode === 'canvas'
                    ? 'bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200 shadow-sm'
                    : 'text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300'
                }`}
              >
                <LayoutGrid className="w-3.5 h-3.5" />
                Canvas
              </button>
            </div>

            <DeadlineModal
              isOpen={isModalOpen}
              onOpenChange={setIsModalOpen}
              editingDeadline={editingDeadline}
              formData={formData}
              setFormData={setFormData}
              onSave={handleSaveDeadline}
              onCancel={() => setIsModalOpen(false)}
              onTriggerClick={openAddModal}
            />

            {viewMode === 'list' && (
            <Button
              onClick={() => {
                const next = !isPlanningMode;
                setIsPlanningMode(next);
                if (next) {
                  setIsCalendarCollapsed(false);
                } else {
                  setPlanningSubMode('auto');
                  setManualActiveDeadlineId(null);
                }
              }}
              variant={isPlanningMode ? 'default' : 'outline'}
              className={isPlanningMode
                ? 'bg-blue-600 hover:bg-blue-700 text-white shadow-md'
                : 'border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
              }
            >
              <LayoutGrid className="w-4 h-4 mr-2" />
              {isPlanningMode ? 'Exit Planning' : 'Planning Mode'}
            </Button>
            )}

            {isPlanningMode && (
              <>
                <div className="flex bg-slate-100 dark:bg-slate-800 rounded-lg p-0.5">
                  <button
                    onClick={() => { setPlanningSubMode('auto'); setManualActiveDeadlineId(null); }}
                    className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all ${
                      planningSubMode === 'auto'
                        ? 'bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-100 shadow-sm'
                        : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'
                    }`}
                  >
                    Auto
                  </button>
                  <button
                    onClick={() => setPlanningSubMode('manual')}
                    className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all ${
                      planningSubMode === 'manual'
                        ? 'bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-100 shadow-sm'
                        : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'
                    }`}
                  >
                    Manual
                  </button>
                </div>

                <SnapshotManager
                  snapshots={snapshots}
                  deadlines={deadlines}
                  onSave={saveSnapshot}
                  onDelete={deleteSnapshot}
                  onLoad={(snapshot) => {
                    const snapshotMap = new Map(snapshot.deadlines.map(d => [d.id, d.daysNeeded]));
                    setDeadlines(prev => prev.map(d => ({
                      ...d,
                      daysNeeded: snapshotMap.has(d.id) ? snapshotMap.get(d.id) : d.daysNeeded
                    })));
                    if (snapshot.manualPlan) {
                      loadManualPlan(snapshot.manualPlan);
                    }
                  }}
                  onExportText={exportSnapshotAsText}
                  manualPlan={manualPlan}
                />
              </>
            )}
          </div>

          {/* Planning toolbars */}
          {isPlanningMode && planningSubMode === 'auto' && deadlines.some(d => d.daysNeeded) && (
            <div className="flex justify-center mb-6">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setDeadlines(prev => prev.map(d => ({ ...d, daysNeeded: null })))}
                className="h-8 text-xs text-red-600 dark:text-red-400 border-red-300 dark:border-red-700 hover:bg-red-50 dark:hover:bg-red-900/20"
              >
                Clear All Auto
              </Button>
            </div>
          )}
          {isPlanningMode && planningSubMode === 'manual' && (
            <div className="flex justify-center items-center gap-3 mb-6">
              <ManualPlanningToolbar
                selectedDeadline={deadlines.find(d => d.id === manualActiveDeadlineId)}
                selectedColorIndex={manualPlan[manualActiveDeadlineId]?.colorIndex ?? 0}
                onColorChange={(colorIndex) => manualActiveDeadlineId && setColor(manualActiveDeadlineId, colorIndex)}
                onClear={() => manualActiveDeadlineId && clearDeadline(manualActiveDeadlineId)}
                dayCount={manualPlan[manualActiveDeadlineId]?.days?.length || 0}
              />
              {Object.keys(manualPlan).some(id => manualPlan[id]?.days?.length > 0) && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => { clearAllManual(); setManualActiveDeadlineId(null); }}
                  className="h-8 text-xs text-red-600 dark:text-red-400 border-red-300 dark:border-red-700 hover:bg-red-50 dark:hover:bg-red-900/20"
                >
                  Clear All Manual
                </Button>
              )}
            </div>
          )}

          {/* Deadlines Sections */}
          {deadlines.length === 0 ? (
            <div className="text-center py-16">
              <Clock className="w-16 h-16 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
              <p className="text-slate-500 dark:text-slate-400 text-lg">Nothing to track yet</p>
              <p className="text-slate-500 dark:text-slate-400 text-sm mt-2">Add your first deadline to get started</p>
            </div>
          ) : viewMode === 'canvas' ? (
            <>
              {/* Canvas toolbar: temporary toggle */}
              <div className="flex items-center justify-end mb-3 gap-3">
                <button
                  onClick={() => setShowTemporaryInCanvas(v => !v)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                    showTemporaryInCanvas
                      ? 'bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-800 text-blue-600 dark:text-blue-400'
                      : 'border-slate-200 dark:border-slate-700 text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300'
                  }`}
                >
                  Temporary
                </button>
              </div>
              <CanvasView
                items={deadlines.filter(d => showTemporaryInCanvas ? true : !(d.isRecurring && new Date(d.dueDate).getTime() > currentTime.getTime()))}
                getPositions={getPositions}
                savePosition={savePosition}
                onReset={resetPositions}
                renderCard={(deadline) => {
                  const timeLeft = calculateTimeLeft(deadline.dueDate);
                  const { progressColor } = getDeadlineMetrics(timeLeft, deadline);
                  const dueStr = new Date(deadline.dueDate).toLocaleDateString('en-GB', { day: '2-digit', month: '2-digit' });
                  const accentColor = deadline.isMarked ? '#10b981'
                    : timeLeft.isOverdue ? '#ef4444'
                    : progressColor.includes('green') ? '#22c55e'
                    : progressColor.includes('yellow') ? '#eab308'
                    : '#ef4444';
                  return (
                    <div
                      className={`w-52 rounded-xl shadow-md border overflow-hidden select-none ${
                        deadline.isMarked
                          ? 'bg-emerald-50 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-800'
                          : 'bg-white dark:bg-slate-800 border-slate-100 dark:border-slate-700'
                      }`}
                      style={{ borderLeft: `4px solid ${accentColor}` }}
                    >
                      <div className="px-3 pt-3 pb-2">
                        <p className="text-sm font-bold text-slate-800 dark:text-slate-100 truncate leading-tight">{deadline.name}</p>
                        <p className="text-xs text-slate-500 dark:text-slate-400 truncate mt-0.5">{deadline.task}</p>
                      </div>
                      <div className="flex items-center justify-between px-3 pb-2.5">
                        <span
                          className="text-xs font-semibold px-1.5 py-0.5 rounded"
                          style={{ color: accentColor, background: `${accentColor}18` }}
                        >
                          {deadline.isMarked ? 'marked' : timeLeft.isOverdue ? 'overdue' : dueStr}
                        </span>
                        <div className="flex items-center gap-1.5">
                          <button
                            onPointerDown={e => e.stopPropagation()}
                            onClick={e => { e.stopPropagation(); handleToggleMarked(deadline.id); }}
                            className={`transition-colors ${
                              deadline.isMarked
                                ? 'text-emerald-500 dark:text-emerald-400 hover:text-slate-400 dark:hover:text-slate-500'
                                : 'text-slate-300 dark:text-slate-600 hover:text-emerald-500 dark:hover:text-emerald-400'
                            }`}
                            title={deadline.isMarked ? 'Unmark' : 'Mark'}
                          >
                            <CheckCircle2 className="w-4 h-4" />
                          </button>
                          <button
                            onPointerDown={e => e.stopPropagation()}
                            onClick={e => { e.stopPropagation(); handleDeleteDeadline(deadline.id); }}
                            className="text-slate-300 dark:text-slate-600 hover:text-rose-500 dark:hover:text-rose-400 transition-colors"
                            title="Delete"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onPointerDown={e => e.stopPropagation()}
                            onClick={e => { e.stopPropagation(); handleCompleteDeadline(deadline.id); }}
                            className="text-slate-300 dark:text-slate-600 hover:text-emerald-500 dark:hover:text-emerald-400 transition-colors"
                            title="Done"
                          >
                            <CheckCircle2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                }}
              />
            </>
          ) : (
            <div className="space-y-12">
              {(() => {
                const { recurring, regular } = getFilteredDeadlines();

                return (
                  <>
                    {/* Common Deadlines Section - now first */}
                    <div>
                      <h2 className="text-2xl font-semibold text-slate-800 dark:text-slate-100 mb-6 text-center">Common</h2>
                      {regular.length === 0 ? (
                        <div className="text-center py-8">
                          <p className="text-slate-500 dark:text-slate-400">No common deadlines</p>
                        </div>
                      ) : (
                        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-8 justify-items-center">
                          {regular.map((deadline) => renderDeadlineCard(deadline, true))}
                        </div>
                      )}
                    </div>

                    {/* Temporary Deadlines Section - now second and collapsible */}
                    <Collapsible open={!isTemporaryCollapsed} onOpenChange={(open) => setIsTemporaryCollapsed(!open)}>
                      <div>
                        <CollapsibleTrigger asChild>
                          <Button
                            variant="ghost"
                            className="w-full text-2xl font-semibold text-slate-800 dark:text-slate-100 mb-6 hover:bg-slate-100 dark:hover:bg-slate-800 p-4 flex items-center justify-center gap-2"
                          >
                            Temporary
                            {isTemporaryCollapsed ?
                              <ChevronDown className="w-5 h-5" /> :
                              <ChevronUp className="w-5 h-5" />
                            }
                          </Button>
                        </CollapsibleTrigger>

                        <CollapsibleContent className="space-y-4">
                          {recurring.length === 0 ? (
                            <div className="text-center py-8">
                              <p className="text-slate-500 dark:text-slate-400">No active temporary deadlines</p>
                            </div>
                          ) : (
                            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-8 justify-items-center">
                              {recurring.map((deadline) => renderDeadlineCard(deadline, false))}
                            </div>
                          )}
                        </CollapsibleContent>
                      </div>
                    </Collapsible>
                  </>
                );
              })()}
            </div>
          )}

          {/* Calendar Section - collapsible, below cards */}
          <div className="mt-12">
            <Collapsible open={!isCalendarCollapsed} onOpenChange={(open) => setIsCalendarCollapsed(!open)}>
              <CollapsibleTrigger asChild>
                <Button
                  variant="ghost"
                  className="w-full text-2xl font-semibold text-slate-800 dark:text-slate-100 mb-6 hover:bg-slate-100 dark:hover:bg-slate-800 p-4 flex items-center justify-center gap-2"
                >
                  <CalendarIcon className="w-5 h-5" />
                  Calendar
                  {isCalendarCollapsed ?
                    <ChevronDown className="w-5 h-5" /> :
                    <ChevronUp className="w-5 h-5" />
                  }
                </Button>
              </CollapsibleTrigger>
              <CollapsibleContent>
                <DeadlineCalendar
                  deadlines={deadlines}
                  isPlanningMode={isPlanningMode}
                  planningSubMode={planningSubMode}
                  manualPlan={manualPlan}
                  manualActiveDeadlineId={manualActiveDeadlineId}
                  onDayClick={handleDayClick}
                />
              </CollapsibleContent>
            </Collapsible>
          </div>

          {/* Statistics */}
          <StatsPanel refreshKey={statsKey} />
          </>
          )}
        </div>
      </div>
    </TooltipProvider>
  );
};

export default DeadlineTracker;
