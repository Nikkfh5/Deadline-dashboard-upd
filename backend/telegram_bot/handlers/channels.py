import logging
import re
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from services.database import get_db
from telegram_bot.utils import get_current_user

logger = logging.getLogger(__name__)


def _normalize_channel(text: str) -> str:
    """Normalize channel input. Returns:
    - 'invite:HASH' for private invite links (t.me/+HASH or t.me/joinchat/HASH)
    - '@username' for public channels
    """
    text = text.strip()
    # Handle t.me invite links: t.me/+HASH or t.me/joinchat/HASH
    match = re.match(r'https?://t\.me/\+(\S+)', text)
    if match:
        return f"invite:{match.group(1)}"
    match = re.match(r'https?://t\.me/joinchat/(\S+)', text)
    if match:
        return f"invite:{match.group(1)}"
    # Handle t.me/username (public)
    match = re.match(r'https?://t\.me/(\S+)', text)
    if match:
        return f"@{match.group(1)}"
    # Handle raw invite hash
    if text.startswith('+'):
        return f"invite:{text[1:]}"
    # Regular username
    if not text.startswith('@'):
        text = f"@{text}"
    return text


async def add_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Укажи канал:\n/add_channel @channelname\n"
            "или\n/add_channel https://t.me/channelname"
        )
        return

    channel = _normalize_channel(" ".join(context.args))
    user = await get_current_user(update)
    if not user:
        return

    db = get_db()
    user_id = str(user["_id"])

    existing = await db.sources.find_one({
        "user_id": user_id,
        "type": "telegram_channel",
        "identifier": channel,
    })

    if existing and existing.get("is_active", True):
        await update.message.reply_text(f"Канал {channel} уже отслеживается.")
        return

    if existing:
        await db.sources.update_one(
            {"_id": existing["_id"]},
            {"$set": {"is_active": True, "updated_at": datetime.utcnow()}},
        )
    else:
        now = datetime.utcnow()
        await db.sources.insert_one({
            "user_id": user_id,
            "type": "telegram_channel",
            "identifier": channel,
            "display_name": channel,
            "is_active": True,
            "joined": False,
            "last_checked_at": None,
            "last_post_id": None,
            "last_content_hash": None,
            "created_at": now,
            "updated_at": now,
        })

    await update.message.reply_text(
        f"Канал {channel} добавлен!\n"
        f"Бот начнёт мониторить новые посты и искать дедлайны."
    )
    logger.info(f"User {update.effective_user.id} added channel {channel}")


async def remove_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Укажи канал: /remove_channel @channelname")
        return

    channel = _normalize_channel(" ".join(context.args))
    user = await get_current_user(update)
    if not user:
        return

    db = get_db()
    result = await db.sources.update_one(
        {"user_id": str(user["_id"]), "type": "telegram_channel", "identifier": channel},
        {"$set": {"is_active": False, "updated_at": datetime.utcnow()}},
    )

    if result.modified_count == 0:
        await update.message.reply_text(f"Канал {channel} не найден в твоих источниках.")
    else:
        await update.message.reply_text(f"Канал {channel} удалён из мониторинга.")


async def list_channels_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_current_user(update)
    if not user:
        return

    db = get_db()
    sources = await db.sources.find({
        "user_id": str(user["_id"]),
        "type": "telegram_channel",
        "is_active": True,
    }).to_list(100)

    if not sources:
        await update.message.reply_text(
            "У тебя нет отслеживаемых каналов.\n"
            "Добавь: /add_channel @channelname"
        )
        return

    lines = ["Отслеживаемые каналы:\n"]
    for s in sources:
        status = "+" if s.get("joined") else "..."
        lines.append(f"[{status}] {s['identifier']}")

    lines.append("\n[+] = подключён, [...] = подключается")
    await update.message.reply_text("\n".join(lines))
