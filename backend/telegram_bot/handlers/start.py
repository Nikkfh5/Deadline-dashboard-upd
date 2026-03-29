import logging
import os
import uuid
from datetime import datetime

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, filters, MessageHandler

from services.database import get_db

logger = logging.getLogger(__name__)


REPLY_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("Добавить дедлайн"), KeyboardButton("Мои дедлайны")],
        [KeyboardButton("Добавить канал"), KeyboardButton("Добавить wiki")],
        [KeyboardButton("Дашборд"), KeyboardButton("Поделиться")],
    ],
    resize_keyboard=True,
    is_persistent=True,
)


async def reply_keyboard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle reply keyboard button presses."""
    text = update.message.text

    if text == "Добавить дедлайн":
        from telegram_bot.handlers.add_deadline import add_command
        await add_command(update, context)
    elif text == "Мои дедлайны":
        from telegram_bot.handlers.deadlines import my_deadlines_command
        await my_deadlines_command(update, context)
    elif text == "Добавить канал":
        from telegram_bot.handlers.channels import add_channel_command
        context.args = []
        await add_channel_command(update, context)
    elif text == "Добавить wiki":
        from telegram_bot.handlers.wiki import add_wiki_command
        context.args = []
        await add_wiki_command(update, context)
    elif text == "Дашборд":
        await dashboard_command(update, context)
    elif text == "Поделиться":
        from telegram_bot.handlers.settings import share_command
        await share_command(update, context)


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
                "reminder_minutes": [1440, 60],
            },
            "created_at": now,
            "updated_at": now,
        }
        await db.users.insert_one(doc)
        logger.info(f"New user registered: {user.id} ({user.first_name})")

    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    dashboard_link = f"{frontend_url}?token={token}"

    await update.message.reply_text(
        f"Привет, {user.first_name}!\n\n"
        f"Я помогу отслеживать дедлайны из Telegram-каналов и вики.\n\n"
        f"Твой дашборд: {dashboard_link}",
        reply_markup=REPLY_KEYBOARD,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Используй кнопки внизу или команды:\n\n"
        "/add — добавить дедлайн\n"
        "/add_channel — добавить канал\n"
        "/add_wiki — добавить wiki\n"
        "/my_deadlines — дедлайны\n"
        "/dashboard — ссылка на дашборд\n"
        "/share — поделиться\n"
        "/join КОД — подключить источники",
        reply_markup=REPLY_KEYBOARD,
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
