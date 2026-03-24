# Deadline Dashboard

Дашборд для отслеживания учебных дедлайнов ФКН ВШЭ. Дедлайны добавляются автоматически через Telegram-бот: бот мониторит каналы и вики-страницы, анализирует посты через Claude Haiku и добавляет дедлайны на дашборд.

## Как это работает

```
Ты в Telegram                    Дашборд в браузере
     |                                  |
     |  /add_channel @cs_hse_matan      |
     |  /add_wiki wiki.cs.hse.ru/...    |
     |                                  |
     v                                  v
  TG Бот ──> Userbot слушает каналы ──> Claude Haiku анализирует посты
                                            |
                                            v
                                     MongoDB (дедлайны)
                                            |
                                            v
                                     Дашборд показывает
```

1. Пишешь боту `/start` — получаешь ссылку на дашборд
2. Добавляешь источники: TG-каналы (`/add_channel`) или wiki-страницы (`/add_wiki`)
3. Бот сам парсит новые посты и обновления, извлекает дедлайны через ИИ
4. Дедлайны появляются на дашборде автоматически

Дашборд также работает как standalone — можно добавлять дедлайны вручную, они сохраняются в localStorage.

## Быстрый старт

### Что нужно

- Python 3.9+
- Node.js 16+ и Yarn
- MongoDB (локально или Docker)
- Telegram Bot Token (от [@BotFather](https://t.me/BotFather))
- Telegram API credentials (от [my.telegram.org](https://my.telegram.org))
- Anthropic API Key (от [console.anthropic.com](https://console.anthropic.com))

### 1. Клонируй и установи

```bash
git clone https://github.com/Nikkfh5/Deadline-dashboard-upd.git
cd Deadline-dashboard-upd

# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd ../frontend
yarn install
```

### 2. Настрой переменные окружения

```bash
cd backend
cp .env.example .env
```

Заполни `backend/.env`:

```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=deadline_tracker
CORS_ORIGINS=http://localhost:3000

TELEGRAM_BOT_TOKEN=123456:ABC-DEF...        # от @BotFather
TELEGRAM_API_ID=12345678                     # от my.telegram.org
TELEGRAM_API_HASH=abc123def456               # от my.telegram.org
TELEGRAM_SESSION_STRING=                     # сгенерируй на шаге 3
ANTHROPIC_API_KEY=sk-ant-...                 # от console.anthropic.com
FRONTEND_URL=http://localhost:3000           # URL дашборда для ссылок в боте
```

### 3. Сгенерируй Telethon-сессию

Нужен отдельный Telegram-аккаунт (номер телефона) для userbot:

```bash
cd backend
python scripts/generate_session.py
```

Введёшь API_ID, API_HASH, номер телефона, код из Telegram. Скопируй полученную строку в `.env` → `TELEGRAM_SESSION_STRING`.

### 4. Запусти

```bash
# Терминал 1: MongoDB
mongod
# или: docker run -d -p 27017:27017 mongo

# Терминал 2: Backend (поднимает API + бот + userbot + scheduler)
cd backend
uvicorn server:app --host 0.0.0.0 --port 8001

# Терминал 3: Frontend
cd frontend
yarn start
```

### 5. Открой

- Дашборд: http://localhost:3000
- Напиши боту `/start` в Telegram — получишь ссылку с токеном

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Регистрация + ссылка на дашборд |
| `/add_channel @name` | Начать мониторинг TG-канала |
| `/remove_channel @name` | Убрать канал |
| `/list_channels` | Список каналов |
| `/add_wiki <url>` | Добавить wiki-страницу |
| `/remove_wiki <url>` | Убрать wiki |
| `/list_wikis` | Список wiki |
| `/my_deadlines` | Ближайшие дедлайны |
| `/dashboard` | Ссылка на дашборд |

## Структура проекта

```
backend/
├── server.py                  # FastAPI — точка входа, lifespan (бот + userbot + scheduler)
├── models/                    # Pydantic-модели: deadline, user, source, parsed_post
├── routers/                   # API: /api/deadlines, /api/users, /api/sources
├── services/
│   ├── database.py            # MongoDB (Motor async) + индексы
│   ├── haiku_analyzer.py      # Claude Haiku — анализ постов и wiki
│   ├── wiki_parser.py         # BeautifulSoup — парсинг таблиц wiki.cs.hse.ru
│   ├── deadline_extractor.py  # Извлечение и дедупликация дедлайнов
│   └── auth.py                # Token-based авторизация
├── telegram_bot/              # python-telegram-bot: команды, хендлеры
├── telegram_userbot/          # Telethon: мониторинг каналов, автовступление
├── scheduler/                 # APScheduler: wiki каждый час, join каналов каждые 5 мин
├── scripts/
│   └── generate_session.py    # Генерация Telethon StringSession
├── tests/                     # pytest: модели, парсер, промпты, утилиты
├── .env.example               # Шаблон переменных окружения
└── requirements.txt

frontend/
├── src/
│   ├── components/
│   │   ├── DeadlineTracker.jsx  # Главный компонент — таймеры, прогресс, CRUD
│   │   └── ui/                  # Shadcn UI компоненты (Radix)
│   ├── services/
│   │   └── api.js               # Axios — sync с бэкендом по токену
│   ├── App.js
│   └── mock.js                  # Моковые данные для работы без бэкенда
└── package.json
```

## API

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | `/api/deadlines?token=xxx` | Все дедлайны пользователя |
| POST | `/api/deadlines?token=xxx` | Создать дедлайн |
| PUT | `/api/deadlines/{id}?token=xxx` | Обновить |
| DELETE | `/api/deadlines/{id}?token=xxx` | Удалить |
| GET | `/api/` | Health check |

## Стек

**Frontend:** React 19, Tailwind CSS, Radix UI (Shadcn), Axios

**Backend:** FastAPI, MongoDB (Motor), python-telegram-bot, Telethon, Anthropic SDK, APScheduler, BeautifulSoup

## Тесты

```bash
cd backend
python -m pytest tests/ -v
```
