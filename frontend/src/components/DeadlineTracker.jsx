import React, { useState, useEffect } from 'react';
import { Clock, Plus, X, Edit3, MoreVertical, Repeat, ChevronDown, ChevronUp, Moon, Sun, CheckCircle2 } from 'lucide-react';
import { Button } from './ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from './ui/dialog';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Textarea } from './ui/textarea';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from './ui/tooltip';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from './ui/dropdown-menu';
import { Card } from './ui/card';
import { Checkbox } from './ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Badge } from './ui/badge';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from './ui/collapsible';
import { mockDeadlines } from '../mock';
import { fetchDeadlines, createDeadline, updateDeadline, deleteDeadlineApi, completeDeadlineApi, hasToken } from '../services/api';
import StatsPanel from './StatsPanel';

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

  const CircularProgress = ({ percentage, color, isOverdue, isPulsing, children }) => {
    const radius = 45;
    const circumference = 2 * Math.PI * radius;
    const strokeDashoffset = circumference - (percentage / 100) * circumference;

    return (
      <div className="relative w-32 h-32">
        <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
          {/* Background circle */}
          <circle
            cx="50"
            cy="50"
            r={radius}
            stroke="currentColor"
            strokeWidth="2"
            fill="transparent"
            className="text-slate-200 dark:text-slate-700"
          />
          {/* Progress circle */}
          <circle
            cx="50"
            cy="50"
            r={radius}
            stroke="currentColor"
            strokeWidth="3"
            fill="transparent"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            className={`${color} transition-all duration-300 ${isPulsing ? 'animate-pulse' : ''}`}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          {children}
        </div>
      </div>
    );
  };

  const truncateText = (text, maxLength = 25) => {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  // Helper function to render individual deadline card
  const renderDeadlineCard = (deadline, isRegularSection) => {
    const timeLeft = calculateTimeLeft(deadline.dueDate);
    const progressColor = getProgressColor(timeLeft, deadline);
    const progressPercentage = getProgressPercentage(timeLeft, deadline);
    const isPulsing = shouldPulse(timeLeft, deadline);
    const showRepeatButton = deadline.isRecurring && timeLeft.isOverdue;

    return (
      <Card 
        key={deadline.id} 
        className="relative p-6 bg-white dark:bg-slate-800 shadow-md hover:shadow-xl hover:ring-2 hover:ring-slate-300 dark:hover:ring-slate-600 hover:ring-offset-2 dark:hover:ring-offset-slate-900 transition-all duration-200 hover:scale-105 cursor-pointer border border-slate-200 dark:border-slate-700"
        onClick={() => openEditModal(deadline)}
      >
        {/* 3-dot menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              onClick={(e) => e.stopPropagation()}
              className="absolute -top-2 -right-2 w-6 h-6 bg-slate-600 hover:bg-slate-700 text-white rounded-full flex items-center justify-center text-xs transition-colors duration-200 shadow-md"
            >
              <MoreVertical className="w-3 h-3" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-32">
            <DropdownMenuItem 
              onClick={(e) => {
                e.stopPropagation();
                openEditModal(deadline);
              }}
              className="cursor-pointer"
            >
              <Edit3 className="w-4 h-4 mr-2" />
              Edit
            </DropdownMenuItem>
            {showRepeatButton && (
              <DropdownMenuItem 
                onClick={(e) => {
                  e.stopPropagation();
                  handleRepeatDeadline(deadline);
                }}
                className="cursor-pointer text-blue-600 focus:text-blue-600"
              >
                <Repeat className="w-4 h-4 mr-2" />
                Repeat
              </DropdownMenuItem>
            )}
            <DropdownMenuItem
              onClick={(e) => {
                e.stopPropagation();
                handleCompleteDeadline(deadline.id);
              }}
              className="cursor-pointer text-green-600 focus:text-green-600"
            >
              <CheckCircle2 className="w-4 h-4 mr-2" />
              Done
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={(e) => {
                e.stopPropagation();
                handleDeleteDeadline(deadline.id);
              }}
              className="cursor-pointer text-red-600 focus:text-red-600"
            >
              <X className="w-4 h-4 mr-2" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Badge for deadline type */}
        <div className="absolute -top-2 -left-2">
          {deadline.isRecurring && !timeLeft.isOverdue && (
            <Badge variant="outline" className="bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 border-blue-300 dark:border-blue-700 text-xs px-2 py-1">
              every {deadline.intervalDays} days
            </Badge>
          )}
          {showRepeatButton && (
            <Badge variant="outline" className="bg-orange-100 dark:bg-orange-900 text-orange-700 dark:text-orange-300 border-orange-300 dark:border-orange-700 text-xs px-2 py-1">
              repeat
            </Badge>
          )}
        </div>

        <div className="flex flex-col items-center space-y-4 mt-4">
          {/* Circular Progress */}
          <CircularProgress 
            percentage={progressPercentage} 
            color={progressColor}
            isOverdue={timeLeft.isOverdue}
            isPulsing={isPulsing}
          >
            <Clock className="w-6 h-6 text-slate-600 dark:text-slate-400 mb-1" />
            <div className="text-center">
              <div className="text-xs font-mono text-slate-700 dark:text-slate-300">
                {timeLeft.isOverdue ? (
                  <span className="text-red-600 font-semibold">OVERDUE</span>
                ) : (
                  `${timeLeft.days}d ${timeLeft.hours}h`
                )}
              </div>
              <div className="text-xs font-mono text-slate-500 dark:text-slate-400">
                {timeLeft.isOverdue ? '' : `${timeLeft.minutes}m ${timeLeft.seconds}s`}
              </div>
            </div>
          </CircularProgress>

          {/* Name and Task */}
          <div className="text-center">
            <h3 className="font-semibold text-slate-800 dark:text-slate-100 text-lg">{deadline.name}</h3>
            {deadline.task && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <p className="text-xs text-slate-600 dark:text-slate-400 mt-1 cursor-help">
                    {truncateText(deadline.task)}
                  </p>
                </TooltipTrigger>
                <TooltipContent className="max-w-xs">
                  <p>{deadline.task}</p>
                </TooltipContent>
              </Tooltip>
            )}
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              {new Date(deadline.dueDate).toLocaleDateString('ru-RU', {
                timeZone: 'Europe/Moscow',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
              })} {timeLeft.isOverdue ? 'ago' : 'to go'}
            </p>
          </div>

          {/* Repeat Button for regular section */}
          {showRepeatButton && isRegularSection && (
            <Button 
              onClick={(e) => {
                e.stopPropagation();
                handleRepeatDeadline(deadline);
              }}
              className="w-full mt-2 bg-blue-600 hover:bg-blue-700 text-white text-sm py-1"
            >
              <Repeat className="w-4 h-4 mr-1" />
              Repeat
            </Button>
          )}
        </div>
      </Card>
    );
  };

  return (
    <TooltipProvider>
      <div className="min-h-screen bg-slate-50 dark:bg-slate-900 p-6 transition-colors">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="flex justify-between items-center mb-12">
            <div className="flex-1" />
            <h1 className="text-4xl font-bold text-slate-800 dark:text-slate-100 tracking-wide">DEADLINES</h1>
            <div className="flex-1 flex justify-end">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setDarkMode(!darkMode)}
                className="text-slate-600 dark:text-slate-300"
              >
                {darkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
              </Button>
            </div>
          </div>

          {/* Add Deadline Button */}
          <div className="flex justify-center mb-8">
            <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
              <DialogTrigger asChild>
                <Button 
                  onClick={openAddModal}
                  className="bg-slate-700 hover:bg-slate-800 dark:bg-slate-600 dark:hover:bg-slate-500 text-white px-6 py-3 rounded-lg shadow-md hover:shadow-lg transition-all duration-200 hover:scale-105"
                >
                  <Plus className="w-5 h-5 mr-2" />
                  Add Deadline
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-md">
                <DialogHeader>
                  <DialogTitle className="text-slate-800 dark:text-slate-100">
                    {editingDeadline ? 'Edit Deadline' : 'Add New Deadline'}
                  </DialogTitle>
                </DialogHeader>
                <div className="space-y-4 mt-4">
                  <div>
                    <Label htmlFor="name" className="text-slate-700 dark:text-slate-300">Name</Label>
                    <Input
                      id="name"
                      value={formData.name}
                      onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                      placeholder="Enter person's name"
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label htmlFor="task" className="text-slate-700 dark:text-slate-300">Task / Description</Label>
                    <Textarea
                      id="task"
                      value={formData.task}
                      onChange={(e) => setFormData(prev => ({ ...prev, task: e.target.value }))}
                      placeholder="What needs to be done?"
                      className="mt-1 min-h-[80px]"
                    />
                  </div>
                  <div>
                    <Label htmlFor="dueDate" className="text-slate-700 dark:text-slate-300">Due Date & Time (Moscow)</Label>
                    <Input
                      id="dueDate"
                      type="datetime-local"
                      value={formData.dueDate}
                      onChange={(e) => setFormData(prev => ({ ...prev, dueDate: e.target.value }))}
                      className="mt-1"
                    />
                  </div>
                  
                  {/* Recurring Options */}
                  <div className="space-y-3 border-t pt-4">
                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id="isRecurring"
                        checked={formData.isRecurring}
                        onCheckedChange={(checked) => setFormData(prev => ({ ...prev, isRecurring: checked }))}
                      />
                      <Label htmlFor="isRecurring" className="text-slate-700 dark:text-slate-300">
                        Make temporary (recurring)
                      </Label>
                    </div>
                    
                    {formData.isRecurring && (
                      <div>
                        <Label htmlFor="intervalDays" className="text-slate-700 dark:text-slate-300">Period (days)</Label>
                        <Select
                          value={formData.intervalDays}
                          onValueChange={(value) => setFormData(prev => ({ ...prev, intervalDays: value }))}
                        >
                          <SelectTrigger className="mt-1">
                            <SelectValue placeholder="Select period" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="7">7 days (week)</SelectItem>
                            <SelectItem value="14">14 days (2 weeks)</SelectItem>
                            <SelectItem value="30">30 days (month)</SelectItem>
                            <SelectItem value="custom">Custom period...</SelectItem>
                          </SelectContent>
                        </Select>
                        
                        {formData.intervalDays === 'custom' && (
                          <Input
                            type="number"
                            min="1"
                            placeholder="Enter number of days"
                            className="mt-2"
                            value={formData.customDays}
                            onChange={(e) => setFormData(prev => ({ ...prev, customDays: e.target.value }))}
                          />
                        )}
                      </div>
                    )}
                  </div>
                  
                  <div className="flex gap-3 pt-4">
                    <Button
                      onClick={handleSaveDeadline}
                      className="flex-1 bg-blue-600 hover:bg-blue-700 text-white disabled:bg-slate-600 disabled:text-slate-400 disabled:opacity-50"
                      disabled={!formData.name.trim() || !formData.task.trim() || !formData.dueDate ||
                               (formData.isRecurring && formData.intervalDays === 'custom' && !formData.customDays.trim())}
                    >
                      {editingDeadline ? 'Save Changes' : 'Add Deadline'}
                    </Button>
                    <Button 
                      onClick={() => setIsModalOpen(false)}
                      variant="outline"
                      className="flex-1"
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              </DialogContent>
            </Dialog>
          </div>

          {/* Deadlines Sections */}
          {deadlines.length === 0 ? (
            <div className="text-center py-16">
              <Clock className="w-16 h-16 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
              <p className="text-slate-500 text-lg">Nothing to track yet</p>
              <p className="text-slate-400 text-sm mt-2">Add your first deadline to get started</p>
            </div>
          ) : (
            <div className="space-y-12">
              {(() => {
                const { recurring, regular } = getFilteredDeadlines();
                
                return (
                  <>
                    {/* Common Deadlines Section - now first */}
                    <div>
                      <h2 className="text-2xl font-semibold text-slate-700 dark:text-slate-300 mb-6 text-center">Common</h2>
                      {regular.length === 0 ? (
                        <div className="text-center py-8">
                          <p className="text-slate-400">No common deadlines</p>
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
                            className="w-full text-2xl font-semibold text-slate-700 dark:text-slate-300 mb-6 hover:bg-slate-100 dark:hover:bg-slate-800 p-4 flex items-center justify-center gap-2"
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
                              <p className="text-slate-400">No active temporary deadlines</p>
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