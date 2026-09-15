import { migrateDeadline, normalizeServerDeadline } from './deadline-normalization';
import { computeWorkPeriods, getDueDates, isDeadlineDay } from './calendar-utils';
import { format } from 'date-fns';

describe('deadline normalization', () => {
  test('maps server marked state into frontend deadlines', () => {
    const normalized = normalizeServerDeadline({
      id: 'server-1',
      name: 'Course',
      task: 'Upload report',
      due_date: '2026-06-05T20:59:00Z',
      created_at: '2026-06-01T10:00:00Z',
      updated_at: '2026-06-02T10:00:00Z',
      is_marked: true,
      is_important: true,
    });

    expect(normalized.isMarked).toBe(true);
    expect(normalized.isImportant).toBe(true);
  });

  test('migrates old cached deadlines with safe status defaults', () => {
    const migrated = migrateDeadline({
      id: 'local-1',
      name: 'Course',
      task: 'Do work',
      dueDate: '2026-06-05T20:59:00Z',
      createdAt: '2026-06-01T10:00:00Z',
      updatedAt: '2026-06-01T10:00:00Z',
    });

    expect(migrated.isMarked).toBe(false);
    expect(migrated.isImportant).toBe(false);
  });

  test.each([
    ['2026-09-20T21:30:00Z', '2026-09-21'],
    ['2026-12-31T22:00:00Z', '2027-01-01'],
  ])('uses the Moscow calendar day for %s', (dueDate, expectedDay) => {
    const deadlines = [{ id: 'deadline-1', dueDate, daysNeeded: 2 }];
    const day = new Date(`${expectedDay}T00:00:00`);
    expect(format(getDueDates(deadlines)[0], 'yyyy-MM-dd')).toBe(expectedDay);
    expect(isDeadlineDay(day, deadlines)).toBe(true);
    const dates = computeWorkPeriods(deadlines).get('deadline-1').dates;
    expect(dates).toHaveLength(2);
    expect(format(dates[1], 'yyyy-MM-dd')).toBe(expectedDay);
  });
});
