export const normalizeServerDeadline = (d) => ({
  id: d.id,
  name: d.name,
  task: d.task,
  dueDate: d.due_date,
  createdAt: d.created_at,
  updatedAt: d.updated_at,
  isRecurring: d.is_recurring || false,
  intervalDays: d.interval_days,
  lastStartedAt: d.last_started_at || d.created_at,
  daysNeeded: d.days_needed ?? null,
  isMarked: d.is_marked || false,
  _fromServer: true,
});

export const migrateDeadline = (deadline) => ({
  id: deadline.id,
  name: deadline.name,
  task: deadline.task || '',
  dueDate: deadline.dueDate,
  createdAt: deadline.createdAt,
  updatedAt: deadline.updatedAt,
  isRecurring: deadline.isRecurring || false,
  intervalDays: deadline.intervalDays,
  lastStartedAt: deadline.lastStartedAt || deadline.createdAt,
  daysNeeded: deadline.daysNeeded ?? null,
  isMarked: deadline.isMarked || deadline.is_marked || false,
  _fromServer: deadline._fromServer || false,
});
