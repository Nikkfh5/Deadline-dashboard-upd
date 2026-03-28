import logging
import os
import uuid
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from services.database import get_db

logger = logging.getLogger(__name__)

HELP_TEXT = (
    "Доступные команды:\n\n"
    "Дедлайны:\n"
    "/add — добавить дедлайн вручную\n"
    "/my_deadlines — ближайшие дедлайны\n"
    "/dashboard — ссылка на дашборд\n\n"
    "Каналы:\n"
    "/add_channel @name — мониторить канал\n"
    "/remove_channel @name — убрать канал\n"
    "/list_channels — список каналов\n\n"
    "Wiki:\n"
    "/add_wiki URL — добавить wiki-страницу\n"
    "/remove_wiki URL — убрать wiki\n"
    "/list_wikis — список wiki\n\n"
    "Шаринг:\n"
    "/share — код для одногруппников\n"
    "/join КОД — подключить чужие источники\n\n"
    "/help — показать это сообщение"
)


async def _send_and_pin_help(chat_id, context: ContextTypes.DEFAULT_TYPE):
    """Send help message and pin it. Unpin previous help if exists."""
    # Unpin previous pinned help message if we saved its id
    bot_data = context.bot_data
    prev_msg_id = bot_data.get(f"pinned_help_{chat_id}")
    if prev_msg_id:
        try:
            await context.bot.unpin_chat_message(chat_id, prev_msg_id)
        except Exception:
            pass

    msg = await context.bot.send_message(chat_id, HELP_TEXT)
    try:
        await msg.pin(disable_notification=True)
        bot_data[f"pinned_help_{chat_id}"] = msg.message_id
    except Exception as e:
        logger.debug(f"Could not pin help message: {e}")


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
        f"Привет, {user.first_name}!\n\n"
        f"Я помогу отслеживать дедлайны из Telegram-каналов и вики ФКН.\n\n"
        f"Твой дашборд: {dashboard_link}"
    )

    await _send_and_pin_help(update.effective_chat.id, context)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _send_and_pin_help(update.effective_chat.id, context)


async def dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    user = await db.users.find_one({"telegram_id": update.effective_user.id})
    if not user:
        await update.message.reply_text("Сначала запусти бота: /start")
        return

    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    token = user["dashboard_token"]
    await update.message.reply_text(f"📊 Твой дашборд:\n{frontend_url}?token={token}")
