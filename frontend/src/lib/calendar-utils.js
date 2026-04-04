import { subDays, eachDayOfInterval, startOfDay, format, isSameDay } from 'date-fns';

// Chart colors for assigning to deadlines (indexes 0-4 cycle)
export const CHART_COLORS = [
  'var(--chart-1)',
  'var(--chart-2)',
  'var(--chart-3)',
  'var(--chart-4)',
  'var(--chart-5)',
];

// Tailwind-safe color classes for dots
export const DOT_COLORS = [
  'bg-orange-400',
  'bg-teal-500',
  'bg-sky-700',
  'bg-amber-400',
  'bg-rose-400',
];

/**
 * For each deadline with daysNeeded, compute the work period dates.
 * Returns Map<deadlineId, { dates: Date[], colorIndex: number, deadline }>
 */
export function computeWorkPeriods(deadlines) {
  const periods = new Map();
  let colorIdx = 0;

  deadlines.forEach((deadline) => {
    if (!deadline.daysNeeded || deadline.daysNeeded < 1) return;

    const dueDate = startOfDay(new Date(deadline.dueDate));
    const startDate = subDays(dueDate, deadline.daysNeeded - 1);

    const dates = eachDayOfInterval({ start: startDate, end: dueDate });

    periods.set(deadline.id, {
      dates,
      colorIndex: colorIdx % 5,
      deadline,
    });

    colorIdx++;
  });

  return periods;
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
  for (let i = 0; i < 5; i++) {
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
