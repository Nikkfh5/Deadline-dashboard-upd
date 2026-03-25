import logging
import os
import uuid
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from services.database import get_db

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db = get_db()

    existing = await db.users.find_one({"telegram_id": user.id})
    if existing:
        token = existing["dashboard_token"]
    else:
        now = datetime.utcnow()
        token = str(uuid.uuid4())
        doc = {
            "telegram_id": user.id,
            "telegram_username": user.username,
            "first_name": user.first_name or "User",
            "dashboard_token": token,
            "settings": {
                "check_interval_minutes": 60,
                "timezone": "Europe/Moscow",
                "notifications_enabled": True,
            },
            "created_at": now,
            "updated_at": now,
        }
        await db.users.insert_one(doc)
        logger.info(f"New user registered: {user.id} ({user.first_name})")

    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    dashboard_link = f"{frontend_url}?token={token}"

    await update.message.reply_text(
        f"Привет, {user.first_name}! 👋\n\n"
        f"Я помогу отслеживать дедлайны из Telegram-каналов и вики ФКН.\n\n"
        f"📊 Твой дашборд: {dashboard_link}\n\n"
        f"Команды:\n"
        f"/add_channel @name — добавить TG канал\n"
        f"/remove_channel @name — убрать канал\n"
        f"/list_channels — список каналов\n"
        f"/add_wiki URL — добавить wiki-страницу\n"
        f"/remove_wiki URL — убрать wiki\n"
        f"/list_wikis — список wiki\n"
        f"/my_deadlines — ближайшие дедлайны\n"
        f"/dashboard — ссылка на дашборд\n"
        f"/export — экспорт настроек\n"
        f"/import — импорт настроек\n"
        f"/help — помощь"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Доступные команды:\n\n"
        "Каналы:\n"
        "/add_channel @channelname — начать мониторинг канала\n"
        "/remove_channel @channelname — перестать мониторить\n"
        "/list_channels — показать все каналы\n\n"
        "Wiki:\n"
        "/add_wiki URL — добавить wiki-страницу\n"
        "/remove_wiki URL — убрать wiki\n"
        "/list_wikis — показать все wiki\n\n"
        "Дедлайны:\n"
        "/my_deadlines — ближайшие дедлайны\n"
        "/dashboard — ссылка на дашборд\n\n"
        "Настройки:\n"
        "/export — экспорт всех источников в JSON\n"
        "/import {json} — импорт источников из JSON\n\n"
        "Бот автоматически парсит новые посты и обновления wiki, "
        "используя ИИ для извлечения информации о дедлайнах."
    )


async def dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    user = await db.users.find_one({"telegram_id": update.effective_user.id})
    if not user:
        await update.message.reply_text("Сначала запусти бота: /start")
        return

    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    token = user["dashboard_token"]
    await update.message.reply_text(f"📊 Твой дашборд:\n{frontend_url}?token={token}")
