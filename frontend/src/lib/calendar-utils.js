import { subDays, eachDayOfInterval, startOfDay, format, isSameDay } from 'date-fns';

// Chart colors for assigning to deadlines (indexes 0-4 cycle)
export const CHART_COLORS = [
  'var(--chart-1)',
  'var(--chart-2)',
  'var(--chart-3)',
  'var(--chart-4)',
  'var(--chart-5)',
];

// Tailwind-safe color classes for dots (same as manual palette)
export const DOT_COLORS = [
  'bg-red-400',
  'bg-blue-500',
  'bg-emerald-500',
  'bg-amber-400',
  'bg-purple-500',
  'bg-pink-400',
  'bg-cyan-500',
  'bg-lime-500',
];

// Alias for backward compat — same palette used everywhere
export const MANUAL_DOT_COLORS = DOT_COLORS;

// HSLA background colors for manual mode (higher opacity, matching MANUAL_DOT_COLORS)
export const MANUAL_BG_COLORS = [
  'hsla(0, 72%, 51%, 0.25)',      // red
  'hsla(217, 91%, 60%, 0.25)',    // blue
  'hsla(160, 84%, 39%, 0.25)',    // emerald
  'hsla(38, 92%, 50%, 0.25)',     // amber
  'hsla(271, 91%, 65%, 0.25)',    // purple
  'hsla(330, 81%, 60%, 0.25)',    // pink
  'hsla(188, 94%, 43%, 0.25)',    // cyan
  'hsla(84, 81%, 44%, 0.25)',     // lime
];

/**
 * Assign stable, non-repeating colors to deadlines.
 * Color is based on deadline's index in the FULL array (not filtered),
 * so adding/removing daysNeeded from one deadline doesn't shift others.
 */
function buildColorMap(deadlines, manualPlan = {}) {
  // Collect color indices already used by manual planning
  const usedByManual = new Set();
  Object.values(manualPlan).forEach((entry) => {
    if (entry.days?.length > 0 && entry.colorIndex != null) {
      usedByManual.add(entry.colorIndex);
    }
  });

  const colorMap = new Map();
  let nextFree = 0;

  deadlines.forEach((d) => {
    // Find next color index not used by manual (if possible)
    if (usedByManual.size < 8) {
      while (usedByManual.has(nextFree) && nextFree < 8) {
        nextFree++;
      }
    }
    colorMap.set(d.id, nextFree % 8);
    nextFree++;
  });

  return colorMap;
}

/**
 * For each deadline with daysNeeded, compute the work period dates.
 * Returns Map<deadlineId, { dates: Date[], colorIndex: number, deadline }>
 */
export function computeWorkPeriods(deadlines, manualPlan = {}) {
  const periods = new Map();
  const colorMap = buildColorMap(deadlines, manualPlan);

  deadlines.forEach((deadline) => {
    if (!deadline.daysNeeded || deadline.daysNeeded < 1) return;

    const dueDate = startOfDay(new Date(deadline.dueDate));
    const startDate = subDays(dueDate, deadline.daysNeeded - 1);

    const dates = eachDayOfInterval({ start: startDate, end: dueDate });

    periods.set(deadline.id, {
      dates,
      colorIndex: colorMap.get(deadline.id),
      deadline,
    });
  });

  return periods;
}

/**
 * Convert manual plan into the same Map format as computeWorkPeriods.
 * manualPlan: { [deadlineId]: { colorIndex, days: string[] } }
 */
export function computeManualWorkPeriods(deadlines, manualPlan) {
  const periods = new Map();
  const deadlineById = new Map(deadlines.map((d) => [d.id, d]));

  Object.entries(manualPlan).forEach(([deadlineId, entry]) => {
    if (!entry.days || entry.days.length === 0) return;
    const deadline = deadlineById.get(deadlineId);
    if (!deadline) return;

    const dates = entry.days.map((d) => startOfDay(new Date(d + 'T00:00:00')));
    periods.set(deadlineId, {
      dates,
      colorIndex: entry.colorIndex,
      deadline,
    });
  });

  return periods;
}

/**
 * Merge auto and manual work periods — always show both.
 * If a deadline has both auto (daysNeeded) and manual days, both are shown
 * with manual using a 'm_' prefix key to distinguish from auto.
 */
export function mergeWorkPeriods(autoWP, manualWP) {
  const merged = new Map();

  autoWP.forEach((value, deadlineId) => {
    merged.set(deadlineId, value);
  });

  manualWP.forEach((value, deadlineId) => {
    if (merged.has(deadlineId)) {
      // Both auto and manual exist — add manual with prefix
      merged.set('m_' + deadlineId, value);
    } else {
      merged.set(deadlineId, value);
    }
  });

  return merged;
}

/**
 * Build a map of date -> deadlineIds[] for overlap detection
 * Returns Map<"YYYY-MM-DD", string[]>
 */
export function computeDayOverlapMap(workPeriods) {
  const overlapMap = new Map();

  workPeriods.forEach(({ dates }, deadlineId) => {
    dates.forEach((date) => {
      const key = format(date, 'yyyy-MM-dd');
      if (!overlapMap.has(key)) {
        overlapMap.set(key, []);
      }
      overlapMap.get(key).push(deadlineId);
    });
  });

  return overlapMap;
}

/**
 * Get all due dates as Date objects
 */
export function getDueDates(deadlines) {
  return deadlines.map((d) => startOfDay(new Date(d.dueDate)));
}

/**
 * Check if a given date is a due date of any deadline
 */
export function isDeadlineDay(date, deadlines) {
  const day = startOfDay(date);
  return deadlines.some((d) => isSameDay(startOfDay(new Date(d.dueDate)), day));
}

/**
 * Get deadline IDs whose work period covers a given date
 */
export function getDeadlinesForDay(date, workPeriods) {
  const day = startOfDay(date);
  const result = [];

  workPeriods.forEach(({ dates, colorIndex, deadline }, deadlineId) => {
    if (dates.some((d) => isSameDay(d, day))) {
      result.push({ deadlineId, colorIndex, deadline });
    }
  });

  return result;
}

/**
 * Build modifiers object for react-day-picker
 */
export function buildModifiers(deadlines, workPeriods) {
  const dueDates = getDueDates(deadlines);
  const overlapMap = computeDayOverlapMap(workPeriods);

  const modifiers = {
    deadlineDay: dueDates,
  };

  // Work period modifiers per color index
  for (let i = 0; i < 8; i++) {
    modifiers[`wp${i}`] = [];
  }

  workPeriods.forEach(({ dates, colorIndex }) => {
    modifiers[`wp${colorIndex}`].push(...dates);
  });

  // Overlap modifiers
  const overlap2 = [];
  const overlap3plus = [];

  overlapMap.forEach((ids, dateKey) => {
    if (ids.length === 2) {
      overlap2.push(new Date(dateKey + 'T00:00:00'));
    } else if (ids.length >= 3) {
      overlap3plus.push(new Date(dateKey + 'T00:00:00'));
    }
  });

  modifiers.overlap2 = overlap2;
  modifiers.overlap3plus = overlap3plus;

  return modifiers;
}
