import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from services.database import get_db
from services.haiku_analyzer import get_analyzer
from telegram_bot.helpers import format_time_left, format_due_date_msk
from telegram_bot.utils import get_current_user

logger = logging.getLogger(__name__)

# Conversation states
NAME, TASK, DATE_INPUT, CONFIRM = range(4)

# Callback data
CONFIRM_SAVE = "confirm:save"
CONFIRM_CANCEL = "confirm:cancel"
CONFIRM_RESTART = "confirm:restart"


def _confirm_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton("Сохранить", callback_data=CONFIRM_SAVE),
            InlineKeyboardButton("Отмена", callback_data=CONFIRM_CANCEL),
        ],
        [
            InlineKeyboardButton("Заново", callback_data=CONFIRM_RESTART),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def _format_preview(data: dict) -> str:
    due_utc = data["due_date"]
    return (
        f"Проверь и подтверди:\n\n"
        f"{data['name']} — {data['task']}\n"
        f"До: {format_due_date_msk(due_utc)} МСК (через {format_time_left(due_utc)})"
    )


def _parse_date(text: str) -> Optional[datetime]:
    """Parse date from user text input. Supports common formats."""
    text = text.strip()
    now = datetime.utcnow() + timedelta(hours=3)  # Moscow

    formats = [
        "%d.%m.%Y %H:%M",
        "%d.%m.%Y",
        "%d.%m %H:%M",
        "%d.%m",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%d/%m %H:%M",
        "%d/%m",
    ]

    for fmt in formats:
        try:
            parsed = datetime.strptime(text, fmt)
            # If year not in format, use current/next year
            if "%Y" not in fmt:
                parsed = parsed.replace(year=now.year)
                if parsed < now - timedelta(days=1):
                    parsed = parsed.replace(year=now.year + 1)
            # If time not in format, default to 23:59
            if "%H" not in fmt:
                parsed = parsed.replace(hour=23, minute=59)
            # Convert from Moscow to UTC
            return parsed - timedelta(hours=3)
        except ValueError:
            continue
    return None


# --- Handlers ---


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point: /add"""
    user = await get_current_user(update)
    if not user:
        return ConversationHandler.END

    context.user_data["add_deadline"] = {"user_id": str(user["_id"])}
    await update.message.reply_text(
        "Добавляем дедлайн!\n\nВведи название:"
    )
    return NAME


async def subject_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 1: name received, ask for description."""
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("Название не может быть пустым. Попробуй ещё:")
        return NAME

    context.user_data["add_deadline"]["name"] = text
    await update.message.reply_text(
        f"{text}\n\nДобавь описание:"
    )
    return TASK


async def task_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 2: description received, show date keyboard."""
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("Описание не может быть пустым. Попробуй ещё:")
        return TASK

    context.user_data["add_deadline"]["task"] = text
    await update.message.reply_text(
        "Когда дедлайн? Напиши дату, например:\n"
        "  15.04.2026 23:59\n"
        "  15.04\n"
        "  завтра\n"
        "  в пятницу\n"
        "  через 3 дня"
    )
    return DATE_INPUT


async def date_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 3b: custom date entered as text. Try regex first, then Haiku."""
    text = update.message.text

    # Try simple regex formats first
    parsed = _parse_date(text)

    # Fallback to Haiku for natural language ("в пятницу", "через 3 дня", etc.)
    if not parsed:
        parsed = await get_analyzer().parse_date(text)

    if not parsed:
        await update.message.reply_text(
            "Не удалось распознать дату. Попробуй так:\n"
            "  15.04.2026 23:59\n"
            "  15.04\n"
            "  завтра\n"
            "  в пятницу\n"
            "  через 3 дня"
        )
        return DATE_INPUT

    context.user_data["add_deadline"]["due_date"] = parsed

    data = context.user_data["add_deadline"]
    await update.message.reply_text(
        _format_preview(data),
        reply_markup=_confirm_keyboard(),
    )
    return CONFIRM


async def confirm_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 4: confirm / cancel / restart."""
    query = update.callback_query
    await query.answer()

    action = query.data

    if action == CONFIRM_CANCEL:
        await query.edit_message_text("Отменено.")
        context.user_data.pop("add_deadline", None)
        return ConversationHandler.END

    if action == CONFIRM_RESTART:
        context.user_data["add_deadline"] = {
            "user_id": context.user_data["add_deadline"]["user_id"]
        }
        await query.edit_message_text(
            "Начинаем заново!\n\nВведи название:"
        )
        return NAME

    # CONFIRM_SAVE
    data = context.user_data["add_deadline"]
    db = get_db()
    now = datetime.utcnow()

    doc = {
        "id": str(uuid.uuid4()),
        "user_id": data["user_id"],
        "name": data["name"],
        "task": data["task"],
        "due_date": data["due_date"],
        "created_at": now,
        "updated_at": now,
        "is_recurring": False,
        "interval_days": None,
        "last_started_at": None,
        "source": {"type": "manual", "source_id": None, "original_text": None},
        "confidence": None,
        "is_postponed": False,
        "previous_due_date": None,
    }
    await db.deadlines.insert_one(doc)

    await query.edit_message_text(
        f"Дедлайн сохранён!\n\n"
        f"{data['name']} — {data['task']}\n"
        f"До: {format_due_date_msk(data['due_date'])} (МСК)"
    )
    context.user_data.pop("add_deadline", None)
    return ConversationHandler.END


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel conversation via /cancel."""
    context.user_data.pop("add_deadline", None)
    await update.message.reply_text("Добавление дедлайна отменено.")
    return ConversationHandler.END


def build_add_deadline_conversation() -> ConversationHandler:
    """Build and return the ConversationHandler for /add."""
    return ConversationHandler(
        entry_points=[CommandHandler("add", add_command)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, subject_received)],
            TASK: [MessageHandler(filters.TEXT & ~filters.COMMAND, task_received)],
            DATE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, date_text)],
            CONFIRM: [
                CallbackQueryHandler(confirm_button, pattern="^confirm:"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
        conversation_timeout=300,
        per_user=True,
        per_chat=True,
    )
