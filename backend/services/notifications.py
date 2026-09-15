import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from textwrap import shorten

from bson import ObjectId
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest, Forbidden, NetworkError, RetryAfter

from services.database import get_db

logger = logging.getLogger(__name__)
# Snapshot whole imports under delivery_lock; network waits only hold _send_lock.
delivery_lock = asyncio.Lock()
_send_lock = asyncio.Lock()


def _moscow_date(value):
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone(timedelta(hours=3))).strftime("%d.%m.%Y %H:%M МСК")


def _notification_text(deadlines):
    notification = deadlines[0]
    moved = "old_date" in notification
    if moved:
        title = "🔄 Перенос дедлайна" if len(deadlines) == 1 else f"🔄 Перенос дедлайнов ({len(deadlines)})"
    else:
        title = "📌 Добавлен новый дедлайн" if len(deadlines) == 1 else f"📌 Добавлены новые дедлайны ({len(deadlines)})"
    lines = [title, f"Источник: {shorten(notification['source_name'], width=150, placeholder='…')}"]
    shown = 0
    for doc in deadlines[:10]:
        task = shorten(doc["task"], width=350, placeholder="…").replace(" | ", "\n", 1)
        entry = f"\n{shorten(doc['name'], width=100, placeholder='…')} · {task}\n"
        if moved:
            entry += f"Было: {_moscow_date(doc['old_date'])}\nСтало: "
        else:
            entry += "До: "
        entry += _moscow_date(doc["due_date"])
        # Leave room for the overflow hint, including non-BMP characters.
        if len(("\n".join(lines) + entry).encode("utf-16-le")) > 7400:
            break
        lines.append(entry)
        shown += 1
    if shown < len(deadlines):
        lines.append(f"\n… и ещё {len(deadlines) - shown} — в дашборде.")
    return "\n".join(lines)


async def send_pending_notifications():
    """Send persisted import events; retain transient failures for the next job."""
    from telegram_bot.bot import get_bot_app

    bot_app = get_bot_app()
    if not bot_app:
        return

    async with _send_lock:
        db = get_db()
        # Bound each drain while loading each user's complete post as one group.
        for _ in range(100):
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            async with delivery_lock:
                first = await db.deadlines.find_one({
                    "notifications.next_attempt_at": {"$lte": now},
                })
                if not first:
                    return
                notification = next(n for n in first["notifications"] if n["next_attempt_at"] <= now)
                query = {"user_id": first["user_id"], "notifications.id": notification["id"]}
                deadlines = await db.deadlines.find(query).to_list(None)
                events = [n for d in deadlines for n in d["notifications"] if n["id"] == notification["id"]]
            acknowledge = {"$pull": {"notifications": {"id": notification["id"]}}}
            user = await db.users.find_one({"_id": ObjectId(first["user_id"])})
            if not user or not user.get("settings", {}).get("notifications_enabled", True):
                await db.deadlines.update_many(query, acknowledge)
                continue

            if not events:
                continue
            source_url = notification.get("source_url")
            buttons = []
            if source_url:
                buttons.append(InlineKeyboardButton("Исходное сообщение", url=source_url))
            frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
            buttons.append(InlineKeyboardButton(
                "Открыть дашборд", url=f"{frontend_url}?token={user['dashboard_token']}"))
            try:
                await bot_app.bot.send_message(
                    chat_id=user["telegram_id"],
                    text=_notification_text(events),
                    reply_markup=InlineKeyboardMarkup([buttons]),
                    parse_mode=None,
                    disable_web_page_preview=True,
                )
            except (Forbidden, BadRequest) as e:
                logger.warning("Notification rejected for user %s: %s", user["telegram_id"], e)
            except (NetworkError, RetryAfter) as e:
                delay = e.retry_after if isinstance(e, RetryAfter) else 60
                if isinstance(delay, timedelta):
                    delay = delay.total_seconds()
                retry_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=max(1, delay))
                await db.deadlines.update_many(
                    query, {"$set": {"notifications.$[event].next_attempt_at": retry_at}},
                    array_filters=[{"event.id": notification["id"]}],
                )
                logger.warning("Notification for user %s will retry after %s: %s", user["telegram_id"], retry_at, e)
                if isinstance(e, RetryAfter):
                    return
                continue

            # Match the sent event so a newer reschedule cannot be acknowledged.
            await db.deadlines.update_many(query, acknowledge)
