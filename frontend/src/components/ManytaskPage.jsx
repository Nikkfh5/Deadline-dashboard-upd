import React, { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { fetchManytaskStatus, connectManytask, disconnectManytask } from '../services/api';

export default function ManytaskPage() {
  const { search } = useLocation();
  const [status, setStatus] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [identifier, setIdentifier] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [reconnect, setReconnect] = useState(false);

  useEffect(() => {
    let active = true;
    fetchManytaskStatus()
      .then(data => { if (active) setStatus(data); })
      .catch(err => { if (active) setError(err.message); });
    return () => { active = false; };
  }, []);

  const refresh = async () => setStatus(await fetchManytaskStatus());
  const needsLogin = !status?.connected || reconnect;

  const handleConnect = async event => {
    event.preventDefault();
    if (!identifier.trim() || (needsLogin && (!username.trim() || !password))) {
      setError('Укажите ссылку курса, логин и пароль.');
      return;
    }
    const data = { identifier: identifier.trim() };
    if (needsLogin) {
      data.username = username.trim();
      data.password = password;
    }
    setPassword('');
    setError('');
    setBusy(true);
    try {
      await connectManytask(data);
      setIdentifier('');
      setReconnect(false);
      await refresh();
    } catch (err) {
      try { await refresh(); } catch { /* Keep the original connection error. */ }
      setError(err.message);
    } finally {
      setPassword('');
      setBusy(false);
    }
  };

  const handleRemove = async source => {
    if (!window.confirm(`Отключить курс «${source.display_name || source.identifier}»?`)) return;
    setError('');
    setBusy(true);
    try {
      await disconnectManytask(source.id);
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-50 p-6 text-slate-800 dark:bg-slate-900 dark:text-slate-100">
      <div className="mx-auto max-w-2xl space-y-6">
        <Link to={`/${search}`} className="text-sm text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-100">← К дедлайнам</Link>
        <div>
          <h1 className="text-2xl font-semibold">Manytask</h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">Подключите курсы, чтобы получать дедлайны заданий в панели.</p>
        </div>

        {error && <p role="alert" className="rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700 dark:border-rose-900 dark:bg-rose-950 dark:text-rose-300">{error}</p>}
        {!status && !error && <p role="status" className="text-sm text-slate-500">Загрузка…</p>}
        {status && (
          <>
            {!status.configured && <p role="status" className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-200">Manytask не настроен администратором сервера.</p>}
            <form onSubmit={handleConnect} aria-busy={busy} className="space-y-4 rounded-lg border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-800">
              <div className="space-y-1.5">
                <Label htmlFor="manytask-url">Ссылка на курс Manytask</Label>
                <Input id="manytask-url" name="identifier" type="url" required value={identifier} onChange={e => setIdentifier(e.target.value)} placeholder="https://app.manytask.org/python-2026-fall/" disabled={!status.configured || busy} />
              </div>
              {status.connected && (
                <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
                  <input type="checkbox" checked={reconnect} onChange={e => { setReconnect(e.target.checked); setPassword(''); }} disabled={!status.configured || busy} />
                  Войти заново (если сессия истекла)
                </label>
              )}
              {needsLogin && (
                <>
                  <p className="text-sm text-slate-600 dark:text-slate-400">Логин и пароль от GitLab Manytask (gitlab.manytask.org). Пароль используется один раз; на сервере хранится зашифрованная сессия.</p>
                  <div className="space-y-1.5">
                    <Label htmlFor="manytask-username">Логин</Label>
                    <Input id="manytask-username" name="username" autoComplete="username" required value={username} onChange={e => setUsername(e.target.value)} disabled={!status.configured || busy} />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="manytask-password">Пароль</Label>
                    <Input id="manytask-password" name="password" type="password" autoComplete="current-password" required value={password} onChange={e => setPassword(e.target.value)} disabled={!status.configured || busy} />
                  </div>
                </>
              )}
              <Button type="submit" disabled={!status.configured || busy}>{busy ? 'Подключаем…' : 'Добавить курс'}</Button>
            </form>

            <section aria-label="Подключённые курсы" className="space-y-3">
              <h2 className="text-lg font-semibold">Подключённые курсы</h2>
              {status.sources.length === 0 && <p className="text-sm text-slate-500">Пока нет подключённых курсов.</p>}
              {status.sources.map(source => (
                <div key={source.id} className="flex flex-wrap items-start justify-between gap-3 rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
                  <div className="min-w-0 space-y-1 text-sm">
                    <p className="font-medium">{source.display_name || source.identifier}</p>
                    {/^https?:\/\//.test(source.identifier) && <a href={source.identifier} target="_blank" rel="noopener noreferrer" className="block break-all text-slate-600 underline dark:text-slate-300">{source.identifier}</a>}
                    {source.last_checked_at && <p className="text-slate-500 dark:text-slate-400">Проверено: {new Date(source.last_checked_at).toLocaleString('ru-RU', { timeZone: 'Europe/Moscow' })} МСК</p>}
                    {source.last_error && <p className="text-rose-700 dark:text-rose-300">{source.last_error}</p>}
                  </div>
                  <Button type="button" variant="outline" size="sm" onClick={() => handleRemove(source)} disabled={busy}>Отключить</Button>
                </div>
              ))}
            </section>
          </>
        )}
      </div>
    </main>
  );
}
