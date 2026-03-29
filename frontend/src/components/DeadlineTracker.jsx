import React, { useState, useEffect } from 'react';
import { Clock, Plus, Moon, Sun, ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from './ui/button';
import { TooltipProvider } from './ui/tooltip';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from './ui/collapsible';
import { mockDeadlines } from '../mock';
import { fetchDeadlines, createDeadline, updateDeadline, deleteDeadlineApi, completeDeadlineApi, hasToken } from '../services/api';
import StatsPanel from './StatsPanel';
import DeadlineCard from './DeadlineCard';
import DeadlineModal from './DeadlineModal';

// Normalize snake_case server response to camelCase frontend format
const normalizeServerDeadline = (d) => ({
  id: d.id,
  name: d.name,
  task: d.task,
  dueDate: d.due_date,
  createdAt: d.created_at,
  updatedAt: d.updated_at,
  isRecurring: d.is_recurring || false,
  intervalDays: d.interval_days,
  lastStartedAt: d.last_started_at || d.created_at,
  _fromServer: true,
});

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

const DeadlineTracker = () => {
  const [deadlines, setDeadlines] = useState([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingDeadline, setEditingDeadline] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    task: '',
    dueDate: '',
    isRecurring: false,
    intervalDays: '7',
    customDays: ''
  });
  const [currentTime, setCurrentTime] = useState(new Date());
  const [isTemporaryCollapsed, setIsTemporaryCollapsed] = useState(true);
  const [statsKey, setStatsKey] = useState(0);
  const refreshStats = () => setStatsKey(k => k + 1);
  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem('darkMode');
    if (saved !== null) return saved === 'true';
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode);
    localStorage.setItem('darkMode', darkMode);
  }, [darkMode]);

  // Helper function to migrate old data structure to new format
  const migrateDeadline = (deadline) => {
    return {
      id: deadline.id,
      name: deadline.name,
      task: deadline.task || '',
      dueDate: deadline.dueDate,
      createdAt: deadline.createdAt,
      updatedAt: deadline.updatedAt,
      // New fields with defaults for backward compatibility
      isRecurring: deadline.isRecurring || false,
      intervalDays: deadline.intervalDays,
      lastStartedAt: deadline.lastStartedAt || deadline.createdAt
    };
  };

  useEffect(() => {
    const loadDeadlines = async () => {
      // Load local data first
      const saved = localStorage.getItem('deadlines');
      let localDeadlines = [];
      if (saved) {
        localDeadlines = JSON.parse(saved).map(migrateDeadline);
      } else {
        localDeadlines = mockDeadlines.map(migrateDeadline);
      }
      setDeadlines(localDeadlines);

      // If we have a backend token, fetch and merge server deadlines
      if (hasToken()) {
        const serverDeadlines = await fetchDeadlines();
        if (serverDeadlines && serverDeadlines.length > 0) {
          const normalized = serverDeadlines.map(normalizeServerDeadline);
          const merged = mergeDeadlines(normalized, localDeadlines);
          setDeadlines(merged);
          localStorage.setItem('deadlines', JSON.stringify(merged));
        }
      }
    };
    loadDeadlines();
  }, []);

  useEffect(() => {
    // Update current time every second
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Periodic backend sync every 30 seconds
  useEffect(() => {
    if (!hasToken()) return;
    const syncInterval = setInterval(async () => {
      const serverDeadlines = await fetchDeadlines();
      if (serverDeadlines && serverDeadlines.length > 0) {
        const normalized = serverDeadlines.map(normalizeServerDeadline);
        setDeadlines(prev => {
          const merged = mergeDeadlines(normalized, prev);
          // Skip update if nothing changed
          if (JSON.stringify(merged) === JSON.stringify(prev)) return prev;
          return merged;
        });
      }
    }, 30000);
    return () => clearInterval(syncInterval);
  }, []);

  useEffect(() => {
    // Save to localStorage whenever deadlines change
    localStorage.setItem('deadlines', JSON.stringify(deadlines));
  }, [deadlines]);

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

  const getProgressColor = (timeLeft, deadline) => {
    if (timeLeft.isOverdue) return 'stroke-red-500';

    // For recurring deadlines, calculate progress from lastStartedAt
    // For non-recurring deadlines, use createdAt as before
    const now = currentTime.getTime();
    const startTime = deadline.isRecurring && deadline.lastStartedAt
      ? new Date(deadline.lastStartedAt).getTime()
      : new Date(deadline.createdAt).getTime();
    const due = new Date(deadline.dueDate).getTime();

    const totalDuration = due - startTime;
    const elapsed = now - startTime;
    const progress = totalDuration > 0 ? elapsed / totalDuration : 1;

    if (progress < 0.5) return 'stroke-green-500';   // 0-50% elapsed
    if (progress < 0.9) return 'stroke-yellow-500';  // 50-90% elapsed
    return 'stroke-red-500';                         // 90%+ elapsed
  };

  const getProgressPercentage = (timeLeft, deadline) => {
    if (timeLeft.isOverdue) return 0;

    // For recurring deadlines, calculate progress from lastStartedAt
    // For non-recurring deadlines, use createdAt as before
    const now = currentTime.getTime();
    const startTime = deadline.isRecurring && deadline.lastStartedAt
      ? new Date(deadline.lastStartedAt).getTime()
      : new Date(deadline.createdAt).getTime();
    const due = new Date(deadline.dueDate).getTime();

    const totalDuration = due - startTime;
    const elapsed = now - startTime;
    const progress = totalDuration > 0 ? elapsed / totalDuration : 1;

    // Return remaining percentage (100% - elapsed%)
    return Math.max(0, Math.min(100, (1 - progress) * 100));
  };

  const shouldPulse = (timeLeft, deadline) => {
    if (timeLeft.isOverdue) return true;

    // For recurring deadlines, calculate progress from lastStartedAt
    // For non-recurring deadlines, use createdAt as before
    const now = currentTime.getTime();
    const startTime = deadline.isRecurring && deadline.lastStartedAt
      ? new Date(deadline.lastStartedAt).getTime()
      : new Date(deadline.createdAt).getTime();
    const due = new Date(deadline.dueDate).getTime();

    const totalDuration = due - startTime;
    const elapsed = now - startTime;
    const progress = totalDuration > 0 ? elapsed / totalDuration : 1;

    return progress >= 0.9; // Pulse when 90%+ elapsed
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
      updatedAt: now.toISOString()
    };

    setDeadlines(prev => prev.map(d => d.id === deadline.id ? updatedDeadline : d));
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
    setFormData({
      name: '',
      task: '',
      dueDate: '',
      isRecurring: false,
      intervalDays: '7',
      customDays: ''
    });
    setIsModalOpen(true);
  };

  const openEditModal = (deadline) => {
    setEditingDeadline(deadline);
    setFormData({
      name: deadline.name,
      task: deadline.task || '',
      dueDate: formatDateTimeForInput(deadline.dueDate),
      isRecurring: deadline.isRecurring || false,
      intervalDays: deadline.intervalDays ? deadline.intervalDays.toString() : '7',
      customDays: ''
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
        lastStartedAt: newLastStartedAt
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
        lastStartedAt: formData.isRecurring ? now.toISOString() : undefined
      };
      setDeadlines(prev => [...prev, deadline]);
      // Sync create to backend — replace local ID with server ID
      if (hasToken()) {
        createDeadline({
          name: deadline.name,
          task: deadline.task,
          due_date: deadline.dueDate,
          is_recurring: deadline.isRecurring,
          interval_days: deadline.intervalDays,
          last_started_at: deadline.lastStartedAt,
        }).then((serverDeadline) => {
          if (serverDeadline) {
            const normalized = normalizeServerDeadline(serverDeadline);
            setDeadlines(prev => prev.map(d =>
              d.id === deadline.id ? normalized : d
            ));
          }
          refreshStats();
        });
      }
    }

    setFormData({ name: '', task: '', dueDate: '', isRecurring: false, intervalDays: '7', customDays: '' });
    setEditingDeadline(null);
    setIsModalOpen(false);
  };

  const handleDeleteDeadline = (id) => {
    setDeadlines(prev => prev.filter(d => d.id !== id));
    if (hasToken()) {
      deleteDeadlineApi(id).then(refreshStats);
    }
  };

  const handleCompleteDeadline = (id) => {
    setDeadlines(prev => prev.filter(d => d.id !== id));
    if (hasToken()) {
      completeDeadlineApi(id).then(refreshStats);
    }
  };

  // Helper function to render individual deadline card
  const renderDeadlineCard = (deadline, isRegularSection) => {
    const timeLeft = calculateTimeLeft(deadline.dueDate);
    const progressColor = getProgressColor(timeLeft, deadline);
    const progressPercentage = getProgressPercentage(timeLeft, deadline);
    const isPulsing = shouldPulse(timeLeft, deadline);

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
        onRepeat={handleRepeatDeadline}
        isRegularSection={isRegularSection}
      />
    );
  };

  return (
    <TooltipProvider>
      <div className="min-h-screen bg-background p-6 transition-colors">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="flex justify-between items-center mb-12">
            <div className="flex-1" />
            <h1 className="text-4xl font-bold text-foreground tracking-wide">DEADLINES</h1>
            <div className="flex-1 flex justify-end">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setDarkMode(!darkMode)}
                className="text-muted-foreground"
              >
                {darkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
              </Button>
            </div>
          </div>

          {/* Add Deadline Button */}
          <div className="flex justify-center mb-8">
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
          </div>

          {/* Deadlines Sections */}
          {deadlines.length === 0 ? (
            <div className="text-center py-16">
              <Clock className="w-16 h-16 text-muted mx-auto mb-4" />
              <p className="text-muted-foreground text-lg">Nothing to track yet</p>
              <p className="text-muted-foreground text-sm mt-2">Add your first deadline to get started</p>
            </div>
          ) : (
            <div className="space-y-12">
              {(() => {
                const { recurring, regular } = getFilteredDeadlines();

                return (
                  <>
                    {/* Common Deadlines Section - now first */}
                    <div>
                      <h2 className="text-2xl font-semibold text-foreground mb-6 text-center">Common</h2>
                      {regular.length === 0 ? (
                        <div className="text-center py-8">
                          <p className="text-muted-foreground">No common deadlines</p>
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
                            className="w-full text-2xl font-semibold text-foreground mb-6 hover:bg-accent p-4 flex items-center justify-center gap-2"
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
                              <p className="text-muted-foreground">No active temporary deadlines</p>
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

          {/* Statistics */}
          <StatsPanel refreshKey={statsKey} />
        </div>
      </div>
    </TooltipProvider>
  );
};

export default DeadlineTracker;
