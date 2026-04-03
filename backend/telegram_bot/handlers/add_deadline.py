import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, MessageOriginChannel
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

# Reply keyboard buttons that should NOT be captured as text input
_REPLY_BUTTONS = frozenset({
    "Добавить дедлайн", "Добавить канал", "Добавить wiki",
    "Мои дедлайны", "Мои источники", "Настройки",
})
_TEXT_INPUT = filters.TEXT & ~filters.COMMAND & ~filters.Text(_REPLY_BUTTONS)

# Callback data
CONFIRM_SAVE = "confirm:save"
CONFIRM_CANCEL = "confirm:cancel"
CONFIRM_RESTART = "confirm:restart"
CONFIRM_EDIT_DATE = "confirm:edit_date"
STEP_CANCEL = "step:cancel"


def _confirm_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton("Сохранить", callback_data=CONFIRM_SAVE),
            InlineKeyboardButton("Отмена", callback_data=CONFIRM_CANCEL),
        ],
        [
            InlineKeyboardButton("Изменить дату", callback_data=CONFIRM_EDIT_DATE),
            InlineKeyboardButton("Заново", callback_data=CONFIRM_RESTART),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def _cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Отмена", callback_data=STEP_CANCEL)]
    ])


def _format_preview(data: dict) -> str:
    due_utc = data["due_date"]
    task = data["task"]
    if len(task) > 200:
        task = task[:200] + "…"
    return (
        f"Проверь и подтверди:\n\n"
        f"{data['name']} — {task}\n"
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
        "Добавляем дедлайн!\n\nВведи название или перешли сообщение из канала:",
        reply_markup=_cancel_keyboard(),
    )
    return NAME


async def forwarded_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle forwarded message at NAME state — auto-extract deadline info."""
    msg = update.message
    text = msg.text or msg.caption or ""

    if not text:
        await msg.reply_text(
            "Не удалось прочитать сообщение. Введи название:",
            reply_markup=_cancel_keyboard(),
        )
        return NAME

    data = context.user_data["add_deadline"]
    data["original_text"] = text

    # Get channel info from forwarded message
    channel_name = ""
    if isinstance(msg.forward_origin, MessageOriginChannel):
        channel_name = msg.forward_origin.chat.title or ""

    await msg.reply_text("Анализирую сообщение…")

    # Use Haiku to extract deadline from the post
    result = await get_analyzer().analyze_post(text, channel_name=channel_name)

    if result.get("has_deadline") and result.get("deadlines"):
        deadline = result["deadlines"][0]

        subject = deadline.get("subject", "") or channel_name
        task_name = deadline.get("task_name", "")
        details = deadline.get("details", "")

        data["name"] = subject or channel_name or task_name
        data["task"] = task_name
        if details:
            data["task"] += f"\n{details}"

        due_str = deadline.get("due_date", "")
        if due_str:
            try:
                dt = datetime.fromisoformat(due_str)
                data["due_date"] = dt - timedelta(hours=3)  # MSK to UTC
            except ValueError:
                pass

    if "due_date" in data:
        await msg.reply_text(
            _format_preview(data),
            reply_markup=_confirm_keyboard(),
        )
        return CONFIRM

    # Date not extracted — fill what we can, ask for date
    if "name" not in data:
        first_line = text.split("\n")[0][:100]
        data["name"] = channel_name or first_line
    if "task" not in data:
        data["task"] = text[:500]

    await msg.reply_text(
        f"{data['name']}\n\n"
        "Не удалось определить дату. Когда дедлайн?\n"
        "  15.04.2026 23:59\n"
        "  15.04\n"
        "  завтра\n"
        "  в пятницу\n"
        "  через 3 дня",
        reply_markup=_cancel_keyboard(),
    )
    return DATE_INPUT


async def subject_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 1: name received, ask for description."""
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text(
            "Название не может быть пустым. Попробуй ещё:",
            reply_markup=_cancel_keyboard(),
        )
        return NAME

    context.user_data["add_deadline"]["name"] = text
    await update.message.reply_text(
        f"{text}\n\nДобавь описание:",
        reply_markup=_cancel_keyboard(),
    )
    return TASK


async def task_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 2: description received, show date keyboard."""
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text(
            "Описание не может быть пустым. Попробуй ещё:",
            reply_markup=_cancel_keyboard(),
        )
        return TASK

    context.user_data["add_deadline"]["task"] = text
    await update.message.reply_text(
        "Когда дедлайн? Напиши дату, например:\n"
        "  15.04.2026 23:59\n"
        "  15.04\n"
        "  завтра\n"
        "  в пятницу\n"
        "  через 3 дня",
        reply_markup=_cancel_keyboard(),
    )
    return DATE_INPUT


async def date_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 3: custom date entered as text. Try regex first, then Haiku."""
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
            "  через 3 дня",
            reply_markup=_cancel_keyboard(),
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
    """Step 4: confirm / cancel / restart / edit date."""
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
            "Начинаем заново!\n\nВведи название или перешли сообщение из канала:"
        )
        return NAME

    if action == CONFIRM_EDIT_DATE:
        await query.edit_message_text(
            "Когда дедлайн? Напиши новую дату:\n"
            "  15.04.2026 23:59\n"
            "  15.04\n"
            "  завтра\n"
            "  в пятницу\n"
            "  через 3 дня",
            reply_markup=_cancel_keyboard(),
        )
        return DATE_INPUT

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
        "source": {
            "type": "manual",
            "source_id": None,
            "original_text": data.get("original_text"),
        },
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


async def step_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel from inline button at any step."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Добавление дедлайна отменено.")
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
        entry_points=[
            CommandHandler("add", add_command),
            MessageHandler(filters.Text(["Добавить дедлайн"]), add_command),
        ],
        states={
            NAME: [
                MessageHandler(filters.FORWARDED & ~filters.COMMAND, forwarded_received),
                MessageHandler(_TEXT_INPUT, subject_received),
                CallbackQueryHandler(step_cancel, pattern=f"^{STEP_CANCEL}$"),
            ],
            TASK: [
                MessageHandler(_TEXT_INPUT, task_received),
                CallbackQueryHandler(step_cancel, pattern=f"^{STEP_CANCEL}$"),
            ],
            DATE_INPUT: [
                MessageHandler(_TEXT_INPUT, date_text),
                CallbackQueryHandler(step_cancel, pattern=f"^{STEP_CANCEL}$"),
            ],
            CONFIRM: [
                CallbackQueryHandler(confirm_button, pattern="^confirm:"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
        allow_reentry=True,
        conversation_timeout=300,
        per_user=True,
        per_chat=True,
    )
