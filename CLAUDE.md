# Deadline Dashboard

Дашборд для отслеживания учебных дедлайнов с автоимпортом из Telegram-каналов и wiki.

## Stack

- **Backend:** Python 3, FastAPI, Motor (async MongoDB), Pydantic v2
- **Frontend:** React (CRA), Tailwind CSS, shadcn/ui (Radix), Lucide icons
- **DB:** MongoDB (motor 3.3.1), database name: `deadline_tracker`
- **Telegram:** python-telegram-bot (бот) + Telethon (userbot для мониторинга каналов)
- **AI:** Anthropic Claude Haiku — парсинг дедлайнов из текста
- **Scheduling:** APScheduler — фоновые задачи (wiki, каналы, напоминания)

## Commands

```bash
# Backend
cd backend && python -m uvicorn server:app --host 0.0.0.0 --port 8001

# Frontend dev
cd frontend && npm start        # dev server :3000
cd frontend && npm run build    # production build

# Tests
cd backend && python -m pytest tests/

# Linting
cd backend && black . && isort . && flake8
```

## Architecture

```
backend/
  server.py              — FastAPI entrypoint, lifespan (db, bot, userbot, scheduler)
  models/                — Pydantic models (deadline, etc.)
  routers/               — REST API: deadlines, users, sources, stats
  services/
    database.py          — MongoDB connection (motor)
    auth.py              — Token-based auth
    haiku_analyzer.py    — Claude Haiku: parse deadlines from text
    deadline_extractor.py — Save extracted deadlines with dedup
    wiki_parser.py       — Parse wiki pages (BeautifulSoup)
    notifications.py     — Telegram notifications
  telegram_bot/          — python-telegram-bot: команды, добавление дедлайнов
  telegram_userbot/      — Telethon: мониторинг каналов, автоимпорт
  scheduler/jobs/        — APScheduler: wiki_check, channel_check, reminders
  tests/

frontend/src/
  App.js                 — Single route → DeadlineTracker
  components/
    DeadlineTracker.jsx  — Main component (state, polling, CRUD)
    DeadlineCard.jsx     — Карточка дедлайна
    DeadlineCalendar.jsx — Календарь
    DeadlineModal.jsx    — Модалка создания/редактирования
    StatsPanel.jsx       — Статистика
    ManualPlanningToolbar.jsx — Ручное планирование
    SnapshotManager.jsx  — Управление снапшотами
  services/api.js        — API client (fetch)
  hooks/                 — useSnapshots, useManualPlan
```

## API

Auth через query param `?token=<uuid>`. Все эндпоинты требуют токен.

- `GET /api/health` — healthcheck (без токена)
- `GET/POST /api/deadlines` — CRUD дедлайнов
- `PUT /api/deadlines/{id}` — обновление
- `DELETE /api/deadlines/{id}?complete=true` — удаление (с опциональным completion)
- `GET /api/stats/*` — статистика

## Deploy

VPS Aeza `176.124.205.198`, systemd сервисы:

```bash
# Деплой
ssh root@176.124.205.198
cd /root/Deadline-dashboard-upd
git pull

# Backend
systemctl restart deadline-backend

# Frontend (нужен rebuild!)
cd frontend && npm run build
systemctl restart deadline-frontend   # serve -s build -l 3000
```

## Env vars

Backend `.env`:
- `MONGO_URL` — MongoDB connection string
- `TELEGRAM_BOT_TOKEN` — токен бота
- `TELETHON_API_ID`, `TELETHON_API_HASH` — Telethon credentials
- `ANTHROPIC_API_KEY` — для Claude Haiku
- `FRONTEND_URL` / `CORS_ORIGINS` — CORS

## Gotchas

- Frontend отдаётся через `serve -s build` — после git pull нужен `npm run build` + restart, иначе старый билд
- MongoDB на VPS падает при полном диске — следить за местом
- Три точки входа данных в deadlines: REST API (Pydantic), Telegram-бот (`add_deadline.py`), автоимпорт (`deadline_extractor.py`) — валидация должна быть во всех трёх
- `days_needed` валидируется `ge=1` в Pydantic, но фронтенд тоже проверяет
- Календарь расположен под карточками, скрыт в collapsible по умолчанию
- Не заменять `slate-*` цвета на семантические токены — используем hardcoded цвета
