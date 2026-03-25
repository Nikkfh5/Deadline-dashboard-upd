import logging
from bson import ObjectId
from telethon import TelegramClient, events
from telethon.tl.types import Channel

from services.database import get_db
from services.haiku_analyzer import HaikuAnalyzer
from services.deadline_extractor import save_extracted_deadlines

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

_analyzer: HaikuAnalyzer = None
_client: TelegramClient = None
# Cache: channel_id -> {"subject": ..., "context": ...}
_channel_profiles: dict = {}


def setup_handlers(client: TelegramClient):
    global _analyzer, _client
    _analyzer = HaikuAnalyzer()
    _client = client

    @client.on(events.NewMessage())
    async def on_new_message(event):
        try:
            await _handle_message(event)
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)


async def _get_channel_context(chat) -> str:
    """Fetch recent messages from channel to build context for Haiku.
    Cached per channel_id to avoid repeated fetches."""
    channel_id = chat.id

    # Check in-memory cache
    if channel_id in _channel_profiles:
        return _channel_profiles[channel_id]

    # Check DB cache
    db = get_db()
    cached = await db.channel_profiles.find_one({"channel_id": channel_id})
    if cached:
        _channel_profiles[channel_id] = cached["context"]
        return cached["context"]

    # Fetch last 15 messages to build context
    if not _client:
        return ""

    try:
        messages = await _client.get_messages(chat, limit=15)
        texts = []
        for msg in reversed(messages):
            t = msg.text or msg.message or ""
            if t and len(t) > 15:
                texts.append(t[:300])

        context = "\n---\n".join(texts)

        # Cache in DB
        await db.channel_profiles.update_one(
            {"channel_id": channel_id},
            {"$set": {
                "channel_id": channel_id,
                "title": chat.title,
                "username": chat.username,
                "context": context,
            }},
            upsert=True,
        )
        _channel_profiles[channel_id] = context
        logger.info(f"Built channel context for {chat.title} ({len(texts)} messages)")
        return context
    except Exception as e:
        logger.warning(f"Failed to fetch channel context: {e}")
        return ""


async def _handle_message(event):
    chat = await event.get_chat()

    if not isinstance(chat, Channel):
        return

    text = event.message.text or event.message.message or ""
    if not text or len(text) < 10:
        return

    logger.debug(f"Channel message: {chat.title} (id={chat.id}, username={chat.username}): {text[:80]}")

    channel_username = f"@{chat.username}" if chat.username else None
    channel_id = chat.id

    db = get_db()

    # Match by @username, string channel_id, or channel_id field (for private channels)
    match_values = [v for v in [channel_username, str(channel_id)] if v]

    # For private channels, chat.id is the full ID. Try matching all ways.
    sources = await db.sources.find({
        "type": "telegram_channel",
        "is_active": True,
        "$or": [
            {"identifier": {"$in": match_values}},
            {"channel_id": channel_id},
            {"channel_id": {"$in": [channel_id, abs(channel_id)]}},
        ],
    }).to_list(100)

    if not sources:
        logger.debug(f"No sources found for channel {chat.title} (id={channel_id}, username={channel_username})")
        return

    logger.info(f"Processing message from {channel_username or channel_id_str}: {text[:100]}...")

    # Get channel context for better subject detection
    channel_context = await _get_channel_context(chat)

    result = await _analyzer.analyze_post(
        text,
        channel_name=chat.title or channel_username or channel_id_str,
        channel_context=channel_context,
    )

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

        source_ids = [s["_id"] for s in sources]
        await db.sources.update_many(
            {"_id": {"$in": source_ids}},
            {"$set": {"last_post_id": event.message.id}},
        )

        from services.notifications import notify_new_deadlines
        await notify_new_deadlines(user_ids, extracted, chat.title or channel_username or channel_id_str, count)
