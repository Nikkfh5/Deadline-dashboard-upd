import axios from 'axios';
import { connectManytask, fetchManytaskStatus } from './api';

jest.mock('axios', () => ({
  create: jest.fn(() => ({ get: jest.fn(), post: jest.fn(), delete: jest.fn() })),
}));

const client = axios.create.mock.results[0].value;

beforeEach(() => {
  localStorage.setItem('dashboard_token', 'test-token');
  jest.clearAllMocks();
});

test('fetches status with dashboard token', async () => {
  client.get.mockResolvedValue({ data: { configured: true, connected: false, sources: [] } });
  await expect(fetchManytaskStatus()).resolves.toEqual({ configured: true, connected: false, sources: [] });
  expect(client.get).toHaveBeenCalledWith('/sources/manytask', { params: { token: 'test-token' } });
});

test('connect failure exposes safe detail without Axios request data', async () => {
  client.post.mockRejectedValue({
    response: { data: { detail: 'Неверный логин или пароль' } },
    config: { data: '{"password":"secret"}' },
  });
  await expect(connectManytask({ identifier: 'https://app.manytask.org/python-2026-fall/', username: 'student', password: 'secret' }))
    .rejects.toThrow('Неверный логин или пароль');
  expect(client.post).toHaveBeenCalledWith(
    '/sources/manytask',
    { identifier: 'https://app.manytask.org/python-2026-fall/', username: 'student', password: 'secret' },
    { params: { token: 'test-token' }, timeout: 60000 },
  );
});
