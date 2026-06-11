import { migrateDeadline, normalizeServerDeadline } from './deadline-normalization';

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
});
