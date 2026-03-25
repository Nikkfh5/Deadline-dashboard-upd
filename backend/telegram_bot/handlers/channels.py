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


async def _try_join_now(identifier: str, source_doc: dict) -> str:
    """Try to join channel immediately. Returns display name."""
    try:
        from telegram_userbot.channel_manager import join_pending_channels
        from telegram_userbot.client import get_userbot
        client = get_userbot()
        if not client:
            return identifier

        db = get_db()

        if identifier.startswith("invite:"):
            invite_hash = identifier[len("invite:"):]
            from telethon.tl.functions.messages import ImportChatInviteRequest, CheckChatInviteRequest
            from telethon.errors import UserAlreadyParticipantError

            try:
                result = await client(ImportChatInviteRequest(invite_hash))
                chat = result.chats[0] if result.chats else None
            except UserAlreadyParticipantError:
                info = await client(CheckChatInviteRequest(invite_hash))
                chat = getattr(info, "chat", None)

            if chat:
                title = chat.title
                await db.sources.update_one(
                    {"_id": source_doc["_id"]},
                    {"$set": {"joined": True, "display_name": title, "channel_id": chat.id, "updated_at": datetime.utcnow()}},
                )
                logger.info(f"Joined private channel: {title}")
                return title
        else:
            channel = identifier.lstrip("@")
            entity = await client.get_entity(channel)
            from telethon.tl.functions.channels import JoinChannelRequest
            await client(JoinChannelRequest(entity))
            title = getattr(entity, "title", identifier)
            await db.sources.update_one(
                {"_id": source_doc["_id"]},
                {"$set": {"joined": True, "display_name": title, "updated_at": datetime.utcnow()}},
            )
            logger.info(f"Joined public channel: {title}")
            return title
    except Exception as e:
        logger.warning(f"Immediate join failed for {identifier}: {e}")
    return identifier


async def add_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Укажи канал:\n/add_channel @channelname\n"
            "или\n/add_channel https://t.me/channelname\n"
            "или приватную ссылку: /add_channel https://t.me/+XXXXX"
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
        name = existing.get("display_name", channel)
        await update.message.reply_text(f"Канал {name} уже отслеживается.")
        return

    if existing:
        await db.sources.update_one(
            {"_id": existing["_id"]},
            {"$set": {"is_active": True, "joined": False, "updated_at": datetime.utcnow()}},
        )
        source_doc = existing
    else:
        now = datetime.utcnow()
        source_doc = {
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
        }
        result = await db.sources.insert_one(source_doc)
        source_doc["_id"] = result.inserted_id

    # Join in background — don't block the bot response
    import asyncio

    async def _join_background():
        display_name = await _try_join_now(channel, source_doc)
        try:
            if display_name != channel:
                await update.message.reply_text(
                    f"Канал \"{display_name}\" подключён!\n"
                    f"Новые дедлайны будут появляться на дашборде."
                )
            else:
                await update.message.reply_text(
                    f"Канал добавлен, подключение в процессе.\n"
                    f"Бот начнёт мониторить посты в ближайшие минуты."
                )
        except Exception:
            pass  # TG API timeout — not critical
        logger.info(f"User {update.effective_user.id} added channel {channel} -> {display_name}")

    await update.message.reply_text("Канал добавлен! Подключаюсь...")
    asyncio.create_task(_join_background())


async def remove_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Укажи канал: /remove_channel @channelname")
        return

    channel = _normalize_channel(" ".join(context.args))
    user = await get_current_user(update)
    if not user:
        return

    db = get_db()
    user_id = str(user["_id"])

    # Try exact match first, then search by display_name
    source = await db.sources.find_one({
        "user_id": user_id, "type": "telegram_channel", "identifier": channel, "is_active": True,
    })
    if not source:
        # Maybe user typed the display name
        raw_name = " ".join(context.args).strip()
        source = await db.sources.find_one({
            "user_id": user_id, "type": "telegram_channel",
            "display_name": {"$regex": re.escape(raw_name), "$options": "i"},
            "is_active": True,
        })

    if not source:
        await update.message.reply_text("Канал не найден в твоих источниках.\nПосмотри список: /list_channels")
        return

    await db.sources.delete_one({"_id": source["_id"]})
    name = source.get("display_name", source["identifier"])
    await update.message.reply_text(f"Канал \"{name}\" удалён.")


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
        name = s.get("display_name", s["identifier"])
        status = "+" if s.get("joined") else "..."
        lines.append(f"[{status}] {name}")

    lines.append("\n[+] = подключён, [...] = подключается")
    await update.message.reply_text("\n".join(lines))
