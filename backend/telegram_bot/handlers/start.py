import logging
import os
import uuid
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from services.database import get_db

logger = logging.getLogger(__name__)

MENU_CB = "menu:"


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Добавить дедлайн", callback_data=f"{MENU_CB}add"),
            InlineKeyboardButton("Мои дедлайны", callback_data=f"{MENU_CB}deadlines"),
        ],
        [
            InlineKeyboardButton("Добавить канал", callback_data=f"{MENU_CB}add_channel"),
            InlineKeyboardButton("Добавить wiki", callback_data=f"{MENU_CB}add_wiki"),
        ],
        [
            InlineKeyboardButton("Мои источники", callback_data=f"{MENU_CB}sources"),
            InlineKeyboardButton("Дашборд", callback_data=f"{MENU_CB}dashboard"),
        ],
        [
            InlineKeyboardButton("Поделиться", callback_data=f"{MENU_CB}share"),
        ],
    ])


async def send_menu(chat_id, context: ContextTypes.DEFAULT_TYPE, text: str = "Выбери действие:"):
    """Send main menu with inline buttons."""
    bot_data = context.bot_data
    prev_msg_id = bot_data.get(f"menu_{chat_id}")
    if prev_msg_id:
        try:
            await context.bot.delete_message(chat_id, prev_msg_id)
        except Exception:
            pass

    msg = await context.bot.send_message(chat_id, text, reply_markup=main_menu_keyboard())
    bot_data[f"menu_{chat_id}"] = msg.message_id


async def menu_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle main menu button presses."""
    query = update.callback_query
    await query.answer()
    action = query.data.removeprefix(MENU_CB)
    chat_id = query.message.chat_id

    if action == "add":
        await query.edit_message_text("Используй /add чтобы добавить дедлайн.")
    elif action == "deadlines":
        from telegram_bot.handlers.deadlines import my_deadlines_command
        # Simulate command call
        await query.edit_message_text("Загружаю...")
        await my_deadlines_command(update, context)
    elif action == "add_channel":
        await query.edit_message_text("Используй /add_channel чтобы добавить канал.")
    elif action == "add_wiki":
        await query.edit_message_text("Используй /add_wiki чтобы добавить wiki.")
    elif action == "sources":
        from telegram_bot.handlers.channels import list_channels_command
        from telegram_bot.handlers.wiki import list_wikis_command
        await query.edit_message_text("Загружаю...")
        await list_channels_command(update, context)
        await list_wikis_command(update, context)
    elif action == "dashboard":
        from telegram_bot.handlers.start import dashboard_command
        await query.edit_message_text("Загружаю...")
        await dashboard_command(update, context)
    elif action == "share":
        from telegram_bot.handlers.settings import share_command
        await query.edit_message_text("Загружаю...")
        await share_command(update, context)

    # Re-send menu after action
    await send_menu(chat_id, context)


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
        f"Твой дашборд: {dashboard_link}"
    )

    await send_menu(update.effective_chat.id, context)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_menu(update.effective_chat.id, context, text=(
        "Команды:\n"
        "/add — добавить дедлайн\n"
        "/add_channel — добавить канал\n"
        "/add_wiki — добавить wiki\n"
        "/my_deadlines — дедлайны\n"
        "/dashboard — ссылка на дашборд\n"
        "/share — поделиться\n"
        "/join КОД — подключить источники\n\n"
        "Или используй кнопки:"
    ))


async def dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    user = await db.users.find_one({"telegram_id": update.effective_user.id})
    if not user:
        await update.message.reply_text("Сначала запусти бота: /start")
        return

    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    token = user["dashboard_token"]
    await update.message.reply_text(f"📊 Твой дашборд:\n{frontend_url}?token={token}")
