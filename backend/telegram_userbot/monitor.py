import logging
import time
from typing import Optional

from bson import ObjectId
from telethon import TelegramClient, events
from telethon.tl.types import Channel
from telethon.tl.functions.channels import GetFullChannelRequest

from services.database import get_db
from services.haiku_analyzer import get_analyzer
from services.deadline_extractor import save_extracted_deadlines

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

_client: TelegramClient = None
# Cache: channel_id -> {"context": str, "ts": float}
_channel_profiles: dict = {}
_CACHE_TTL = 3600  # 1 hour


def _get_cached_profile(channel_id: int) -> Optional[dict]:
    entry = _channel_profiles.get(channel_id)
    if entry and (time.time() - entry["ts"]) < _CACHE_TTL:
        return entry["profile"]
    return None


def _set_cached_profile(channel_id: int, profile: dict):
    _channel_profiles[channel_id] = {"profile": profile, "ts": time.time()}
    # Evict old entries if cache too large
    if len(_channel_profiles) > 500:
        cutoff = time.time() - _CACHE_TTL
        expired = [k for k, v in _channel_profiles.items() if v["ts"] < cutoff]
        for k in expired:
            del _channel_profiles[k]
        # If still over 500 after TTL eviction, drop the oldest 10%
        if len(_channel_profiles) > 500:
            to_evict = max(1, len(_channel_profiles) // 10)
            oldest_keys = sorted(_channel_profiles, key=lambda k: _channel_profiles[k]["ts"])[:to_evict]
            for k in oldest_keys:
                del _channel_profiles[k]


def setup_handlers(client: TelegramClient):
    global _client
    _client = client

    @client.on(events.NewMessage())
    async def on_new_message(event):
        try:
            await _handle_message(event)
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)


async def _get_channel_profile(chat) -> dict:
    """Fetch channel info: description, recent messages, known subjects.
    Cached per channel_id to avoid repeated fetches."""
    channel_id = chat.id
    empty_profile = {"context": "", "about": "", "known_subjects": []}

    # Check in-memory cache with TTL
    cached = _get_cached_profile(channel_id)
    if cached is not None:
        return cached

    # Check DB cache
    db = get_db()
    cached_doc = await db.channel_profiles.find_one({"channel_id": channel_id})
    if cached_doc:
        profile = {
            "context": cached_doc.get("context", ""),
            "about": cached_doc.get("about", ""),
            "known_subjects": cached_doc.get("known_subjects", []),
        }
        _set_cached_profile(channel_id, profile)
        return profile

    if not _client:
        return empty_profile

    about = ""
    context = ""

    # Fetch channel description
    try:
        full = await _client(GetFullChannelRequest(chat))
        about = full.full_chat.about or ""
    except Exception as e:
        logger.warning(f"Failed to fetch channel about: {e}")

    # Fetch last 15 messages to build context
    try:
        messages = await _client.get_messages(chat, limit=15)
        texts = []
        for msg in reversed(messages):
            t = msg.text or msg.message or ""
            if t and len(t) > 15:
                texts.append(t[:300])
        context = "\n---\n".join(texts)
    except Exception as e:
        logger.warning(f"Failed to fetch channel context: {e}")

    profile = {"context": context, "about": about, "known_subjects": []}

    # Cache in DB
    await db.channel_profiles.update_one(
        {"channel_id": channel_id},
        {"$set": {
            "channel_id": channel_id,
            "title": chat.title,
            "username": chat.username,
            "context": context,
            "about": about,
            "known_subjects": [],
        }},
        upsert=True,
    )
    _set_cached_profile(channel_id, profile)
    logger.info(f"Built channel profile for {chat.title} (about: {about[:80]})")
    return profile


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

    # Filter out users who disabled channel parsing
    user_ids_all = list(set(s["user_id"] for s in sources))
    users_with_parsing = await db.users.find(
        {"_id": {"$in": [ObjectId(uid) for uid in user_ids_all]},
         "settings.channel_parsing_enabled": {"$ne": False}},
    ).to_list(100)
    active_user_ids = set(str(u["_id"]) for u in users_with_parsing)
    sources = [s for s in sources if s["user_id"] in active_user_ids]

    if not sources:
        logger.debug(f"All users disabled parsing for channel {chat.title}")
        return

    logger.info(f"Processing message from {channel_username or str(channel_id)}: {text[:100]}...")

    # Get channel profile for better subject detection
    profile = await _get_channel_profile(chat)

    result = await get_analyzer().analyze_post(
        text,
        channel_name=chat.title or channel_username or str(channel_id),
        channel_context=profile["context"],
        channel_about=profile["about"],
        known_subjects=profile["known_subjects"],
    )

    logger.info(f"Haiku result: has_deadline={result.get('has_deadline')}, deadlines={len(result.get('deadlines', []))}, analysis={result.get('analysis', '')[:150]}")

    if not result.get("has_deadline"):
        return

    extracted = result.get("deadlines", [])
    if not extracted:
        return

    user_ids = list(set(s["user_id"] for s in sources))
    source_id = str(sources[0]["_id"])

    count, rescheduled = await save_extracted_deadlines(
        user_ids=user_ids,
        extracted=extracted,
        source_id=source_id,
        source_type="telegram",
        raw_text=text,
    )

    if count > 0:
        logger.info(f"Added {count} deadlines from {channel_username or str(channel_id)}")

        # Remember extracted subject names for this channel
        new_subjects = list(set(
            d.get("subject", "") for d in extracted
            if d.get("subject") and d["subject"] != "Unknown"
        ))
        if new_subjects:
            await db.channel_profiles.update_one(
                {"channel_id": chat.id},
                {"$addToSet": {"known_subjects": {"$each": new_subjects}}},
            )
            # Update in-memory cache
            entry = _channel_profiles.get(chat.id)
            if entry:
                existing = set(entry["profile"].get("known_subjects", []))
                existing.update(new_subjects)
                entry["profile"]["known_subjects"] = list(existing)

        source_ids = [s["_id"] for s in sources]
        await db.sources.update_many(
            {"_id": {"$in": source_ids}},
            {"$set": {"last_post_id": event.message.id}},
        )

        from services.notifications import notify_new_deadlines
        await notify_new_deadlines(user_ids, extracted, chat.title or channel_username or str(channel_id), count)

    if rescheduled:
        logger.info(f"Rescheduled {len(rescheduled)} deadlines from {channel_username or str(channel_id)}")
        from services.notifications import notify_deadline_moved
        await notify_deadline_moved(user_ids, rescheduled, chat.title or channel_username or str(channel_id))
