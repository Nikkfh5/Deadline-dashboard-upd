import logging
import re
from datetime import datetime

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
from telegram_bot.utils import get_current_user

WAITING_CHANNEL_LINK = 0
DEL_CHANNEL_CB = "del_ch:"

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


async def add_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point: /add_channel — if link provided inline, process it; otherwise ask."""
    user = await get_current_user(update)
    if not user:
        return ConversationHandler.END

    if context.args:
        await _process_channel_link(update, context, " ".join(context.args), user)
        return ConversationHandler.END

    context.user_data["add_channel_user"] = user
    await update.message.reply_text(
        "Отправь ссылку на канал или @username:\n\n"
        "  @channelname\n"
        "  https://t.me/channelname\n"
        "  https://t.me/+XXXXX (приватный)"
    )
    return WAITING_CHANNEL_LINK


async def channel_link_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive channel link in second message."""
    user = context.user_data.pop("add_channel_user", None)
    if not user:
        user = await get_current_user(update)
        if not user:
            return ConversationHandler.END

    await _process_channel_link(update, context, update.message.text.strip(), user)
    return ConversationHandler.END


async def _process_channel_link(update, context, raw_text: str, user: dict):
    """Shared logic for adding a channel."""
    channel = _normalize_channel(raw_text)

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
        except Exception as e:
            logger.debug(f"TG message send failed: {e}")
        logger.info(f"User {update.effective_user.id} added channel {channel} -> {display_name}")

    await update.message.reply_text("Канал добавлен! Подключаюсь...")
    asyncio.create_task(_join_background())


def build_add_channel_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("add_channel", add_channel_command)],
        states={
            WAITING_CHANNEL_LINK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, channel_link_received),
            ],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
        conversation_timeout=120,
        per_user=True,
        per_chat=True,
    )


async def remove_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show channels as buttons for deletion."""
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
        await update.message.reply_text("Нет каналов для удаления.")
        return

    buttons = []
    for s in sources:
        name = s.get("display_name", s["identifier"])
        buttons.append([InlineKeyboardButton(
            f"X  {name}",
            callback_data=f"{DEL_CHANNEL_CB}{s['_id']}",
        )])

    await update.message.reply_text(
        "Нажми на канал чтобы удалить:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def delete_channel_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle channel deletion via inline button."""
    query = update.callback_query
    await query.answer()

    from bson import ObjectId
    source_id = query.data.removeprefix(DEL_CHANNEL_CB)

    db = get_db()
    source = await db.sources.find_one({"_id": ObjectId(source_id)})
    if not source:
        await query.answer("Канал не найден", show_alert=True)
        return

    await db.sources.delete_one({"_id": ObjectId(source_id)})
    name = source.get("display_name", source["identifier"])
    await query.edit_message_text(f"Канал \"{name}\" удалён.")


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

    msg = update.message or update.callback_query.message

    if not sources:
        await msg.reply_text("Нет отслеживаемых каналов.")
        return

    lines = ["<b>Отслеживаемые каналы:</b>\n"]
    for s in sources:
        name = s.get("display_name", s["identifier"])
        identifier = s.get("identifier", "")
        status = "✅" if s.get("joined") else "⏳"
        if identifier.startswith("@"):
            url = f"https://t.me/{identifier[1:]}"
            lines.append(f'{status} <a href="{url}">{name}</a>')
        else:
            lines.append(f"{status} {name}")

    await msg.reply_text("\n".join(lines), parse_mode="HTML", disable_web_page_preview=True)
