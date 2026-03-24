import logging
from bson import ObjectId
from telethon import TelegramClient, events
from telethon.tl.types import Channel

from services.database import get_db
from services.haiku_analyzer import HaikuAnalyzer
from services.deadline_extractor import save_extracted_deadlines

logger = logging.getLogger(__name__)

_analyzer: HaikuAnalyzer = None


def setup_handlers(client: TelegramClient):
    global _analyzer
    _analyzer = HaikuAnalyzer()

    @client.on(events.NewMessage())
    async def on_new_message(event):
        try:
            await _handle_message(event)
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)


async def _handle_message(event):
    chat = await event.get_chat()

    if not isinstance(chat, Channel):
        return

    text = event.message.text or event.message.message or ""
    if not text or len(text) < 10:
        return

    channel_username = f"@{chat.username}" if chat.username else None
    channel_id_str = str(chat.id)

    db = get_db()

    # Build query for matching sources
    match_values = [v for v in [channel_username, channel_id_str] if v]
    sources = await db.sources.find({
        "type": "telegram_channel",
        "identifier": {"$in": match_values},
        "is_active": True,
    }).to_list(100)

    if not sources:
        return

    logger.info(f"Processing message from {channel_username or channel_id_str}: {text[:100]}...")

    result = await _analyzer.analyze_post(text, channel_name=chat.title or channel_username or channel_id_str)

    if not result.get("has_deadline"):
        return

    extracted = result.get("deadlines", [])
    if not extracted:
        return

    user_ids = list(set(s["user_id"] for s in sources))
    source_id = str(sources[0]["_id"])

    count = await save_extracted_deadlines(
        user_ids=user_ids,
        extracted=extracted,
        source_id=source_id,
        source_type="telegram",
        raw_text=text,
    )

    if count > 0:
        logger.info(f"Added {count} deadlines from {channel_username or channel_id_str}")

        # Batch update last_post_id for all matching sources
        source_ids = [s["_id"] for s in sources]
        await db.sources.update_many(
            {"_id": {"$in": source_ids}},
            {"$set": {"last_post_id": event.message.id}},
        )

        from services.notifications import notify_new_deadlines
        await notify_new_deadlines(user_ids, extracted, chat.title or channel_username or channel_id_str, count)


