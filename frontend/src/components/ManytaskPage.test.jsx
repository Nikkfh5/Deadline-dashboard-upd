import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import ManytaskPage from './ManytaskPage';
import { fetchManytaskStatus, connectManytask } from '../services/api';

jest.mock('../services/api', () => ({
  fetchManytaskStatus: jest.fn(),
  connectManytask: jest.fn(),
  disconnectManytask: jest.fn(),
}));

jest.mock('react-router-dom', () => ({
  Link: ({ children, to, ...props }) => <a href={to} {...props}>{children}</a>,
  useLocation: () => global.window.location,
}), { virtual: true });

let container;
let root;

async function renderPage(initialEntries = ['/']) {
  window.history.replaceState({}, '', initialEntries[0]);
  await act(async () => { root.render(<ManytaskPage />); });
}

function change(input, value) {
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
  setter.call(input, value);
  input.dispatchEvent(new Event('input', { bubbles: true }));
}

beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  jest.clearAllMocks();
});

afterEach(async () => {
  await act(async () => { root.unmount(); });
  container.remove();
});

test('disables credential submission when server is not configured', async () => {
  fetchManytaskStatus.mockResolvedValue({ configured: false, connected: false, sources: [] });
  await renderPage();
  expect(container.textContent).toMatch(/не настроен/i);
  expect(container.querySelector('button[type="submit"]').disabled).toBe(true);
});

test('back link keeps the dashboard token in this tab', async () => {
  fetchManytaskStatus.mockResolvedValue({ configured: true, connected: false, sources: [] });
  await renderPage(['/manytask?token=alice']);
  expect(container.querySelector('a[href^="/"]').getAttribute('href')).toBe('/?token=alice');
});

test('clears password after a failed connect and shows only safe error text', async () => {
  fetchManytaskStatus.mockResolvedValue({ configured: true, connected: false, sources: [] });
  connectManytask.mockRejectedValue(new Error('Неверный логин или пароль'));
  await renderPage();
  const url = container.querySelector('input[name="identifier"]');
  const username = container.querySelector('input[name="username"]');
  const password = container.querySelector('input[name="password"]');
  await act(async () => {
    change(url, 'https://app.manytask.org/python-2026-fall/');
    change(username, 'student');
    change(password, 'secret');
  });
  await act(async () => {
    container.querySelector('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
  });
  expect(connectManytask).toHaveBeenCalledWith({ identifier: 'https://app.manytask.org/python-2026-fall/', username: 'student', password: 'secret' });
  expect(password.value).toBe('');
  expect(container.textContent).toContain('Неверный логин или пароль');
  expect(container.textContent).not.toContain('secret');
});

test('connected account adds a course without sending credentials', async () => {
  fetchManytaskStatus.mockResolvedValue({ configured: true, connected: true, sources: [] });
  connectManytask.mockResolvedValue({ id: 'source-1' });
  await renderPage();
  await act(async () => { change(container.querySelector('input[name="identifier"]'), 'https://app.manytask.org/python-2026-fall/'); });
  await act(async () => {
    container.querySelector('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
  });
  expect(connectManytask).toHaveBeenCalledWith({ identifier: 'https://app.manytask.org/python-2026-fall/' });
});

test('expired session reveals login fields and keeps the connect error', async () => {
  fetchManytaskStatus
    .mockResolvedValueOnce({ configured: true, connected: true, sources: [] })
    .mockResolvedValueOnce({ configured: true, connected: false, sources: [] });
  connectManytask.mockRejectedValue(new Error('Сессия Manytask истекла'));
  await renderPage();
  expect(container.querySelector('input[name="password"]')).toBeNull();
  await act(async () => { change(container.querySelector('input[name="identifier"]'), 'https://app.manytask.org/python-2026-fall/'); });
  await act(async () => {
    container.querySelector('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
  });
  expect(fetchManytaskStatus).toHaveBeenCalledTimes(2);
  expect(container.querySelector('input[name="password"]')).not.toBeNull();
  expect(container.textContent).toContain('Сессия Manytask истекла');
});

test('status refresh failure does not replace the connect error', async () => {
  fetchManytaskStatus
    .mockResolvedValueOnce({ configured: true, connected: true, sources: [] })
    .mockRejectedValueOnce(new Error('Не удалось обновить состояние'));
  connectManytask.mockRejectedValue(new Error('Сессия Manytask истекла'));
  await renderPage();
  await act(async () => { change(container.querySelector('input[name="identifier"]'), 'https://app.manytask.org/python-2026-fall/'); });
  await act(async () => {
    container.querySelector('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
  });
  expect(container.textContent).toContain('Сессия Manytask истекла');
  expect(container.textContent).not.toContain('Не удалось обновить состояние');
});
