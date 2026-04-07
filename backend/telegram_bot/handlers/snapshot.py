import logging
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import ContextTypes

from services.database import get_db
from services.deadline_extractor import save_extracted_deadlines, content_hash
from services.haiku_analyzer import get_analyzer
from telegram_bot.utils import get_current_user

logger = logging.getLogger(__name__)

DEFAULT_MSG_LIMIT = 50
MAX_MSG_LIMIT = 200


async def snapshot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Scan message history of tracked channels and extract missed deadlines."""
    user = await get_current_user(update)
    if not user:
        return

    # Parse optional message limit from args: /snapshot 100
    limit = DEFAULT_MSG_LIMIT
    if context.args:
        try:
            limit = min(int(context.args[0]), MAX_MSG_LIMIT)
        except (ValueError, IndexError):
            pass

    user_id = str(user["_id"])
    db = get_db()

    # Get user's active telegram channels
    sources = await db.sources.find({
        "user_id": user_id,
        "type": "telegram_channel",
        "is_active": True,
    }).to_list(100)

    if not sources:
        await update.message.reply_text("У тебя нет отслеживаемых каналов. Добавь через /add_channel")
        return

    # Get Telethon client
    from telegram_userbot.client import get_userbot
    client = get_userbot()
    if not client:
        await update.message.reply_text("Userbot не запущен, snapshot недоступен.")
        return

    status_msg = await update.message.reply_text(
        f"Сканирую историю {len(sources)} канал(ов), последние {limit} сообщений...\n"
        "Это может занять некоторое время."
    )

    total_new = 0
    total_rescheduled = 0
    channel_results = []

    for source in sources:
        channel_name = source.get("display_name", source["identifier"])
        try:
            # Resolve the channel entity
            entity = None
            if source.get("channel_id"):
                try:
                    entity = await client.get_entity(source["channel_id"])
                except Exception:
                    pass

            if not entity:
                identifier = source["identifier"]
                if identifier.startswith("invite:"):
                    # Private channel — can't iterate by invite hash, skip if no channel_id
                    logger.warning(f"Cannot snapshot private channel without channel_id: {identifier}")
                    channel_results.append(f"  • {channel_name} — пропущен (приватный, нет ID)")
                    continue
                entity = await client.get_entity(identifier)

            # Fetch channel profile for context
            from telegram_userbot.monitor import _get_channel_profile
            profile = await _get_channel_profile(entity)

            # Fetch message history
            messages = await client.get_messages(entity, limit=limit)

            source_id = str(source["_id"])
            channel_new = 0
            channel_rescheduled = 0
            skipped = 0

            for msg in messages:
                text = msg.text or msg.message or ""
                if not text or len(text) < 10:
                    continue

                # Check if already parsed
                c_hash = content_hash(text)
                existing = await db.parsed_posts.find_one({
                    "source_id": source_id,
                    "content_hash": c_hash,
                })
                if existing:
                    skipped += 1
                    continue

                # Analyze with Haiku
                result = await get_analyzer().analyze_post(
                    text,
                    channel_name=entity.title or channel_name,
                    channel_context=profile["context"],
                    channel_about=profile["about"],
                    known_subjects=profile.get("known_subjects", []),
                )

                if not result.get("has_deadline"):
                    continue

                extracted = result.get("deadlines", [])
                if not extracted:
                    continue

                # Filter out deadlines that already passed
                now_utc = datetime.utcnow()
                valid = []
                for d in extracted:
                    due_str = d.get("due_date")
                    if not due_str:
                        continue
                    try:
                        due = datetime.fromisoformat(due_str)
                        if due > now_utc:
                            valid.append(d)
                    except (ValueError, TypeError):
                        valid.append(d)  # keep if can't parse — extractor will handle

                if not valid:
                    continue

                count, rescheduled = await save_extracted_deadlines(
                    user_ids=[user_id],
                    extracted=valid,
                    source_id=source_id,
                    source_type="telegram",
                    raw_text=text,
                )
                channel_new += count
                channel_rescheduled += len(rescheduled)

            total_new += channel_new
            total_rescheduled += channel_rescheduled

            parts = []
            if channel_new:
                parts.append(f"+{channel_new} новых")
            if channel_rescheduled:
                parts.append(f"{channel_rescheduled} перенесённых")
            if not parts:
                parts.append("нет новых дедлайнов")

            channel_results.append(f"  • {channel_name} — {', '.join(parts)}")
            logger.info(f"Snapshot {channel_name}: new={channel_new}, rescheduled={channel_rescheduled}, skipped={skipped}")

        except Exception as e:
            logger.error(f"Snapshot error for {channel_name}: {e}", exc_info=True)
            channel_results.append(f"  • {channel_name} — ошибка: {e}")

    # Build result message
    lines = [f"Snapshot завершён!\n"]
    if total_new:
        lines.append(f"Найдено новых дедлайнов: {total_new}")
    if total_rescheduled:
        lines.append(f"Перенесено: {total_rescheduled}")
    if not total_new and not total_rescheduled:
        lines.append("Новых дедлайнов не найдено.")
    lines.append(f"\nПо каналам:")
    lines.extend(channel_results)

    await status_msg.edit_text("\n".join(lines))
