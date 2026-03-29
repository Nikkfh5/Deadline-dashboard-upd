import logging
import os
from datetime import datetime, timedelta

from services.database import get_db

logger = logging.getLogger(__name__)

# Default reminder intervals in minutes (24h and 1h before deadline)
DEFAULT_INTERVALS = [1440, 60]


async def reminders_job():
    """Check upcoming deadlines and send reminders to users."""
    logger.info("Running reminders job...")
    db = get_db()
    now = datetime.utcnow()

    users = await db.users.find({
        "settings.notifications_enabled": True,
    }).to_list(1000)

    if not users:
        return

    total_sent = 0

    for user in users:
        intervals = user.get("settings", {}).get("reminder_minutes", DEFAULT_INTERVALS)

        # 0 means disabled
        if not intervals or intervals == [0] or intervals == 0:
            continue

        if isinstance(intervals, (int, float)):
            intervals = [int(intervals)]

        user_id = str(user["_id"])

        for minutes_before in intervals:
            if minutes_before <= 0:
                continue

            # Find deadlines due in [now + minutes_before - 5min, now + minutes_before + 5min)
            # This 10-minute window ensures we catch deadlines even if job runs slightly late
            # Use $lt (not $lte) on the upper bound to avoid double-firing at boundaries
            window_start = now + timedelta(minutes=minutes_before - 5)
            window_end = now + timedelta(minutes=minutes_before + 5)

            deadlines = await db.deadlines.find({
                "user_id": user_id,
                "due_date": {"$gte": window_start, "$lt": window_end},
                "is_recurring": {"$ne": True},
            }).to_list(50)

            if not deadlines:
                continue

            # Check which ones we already reminded about
            for d in deadlines:
                reminder_key = f"{d['id']}_{minutes_before}"

                already_sent = await db.reminders_sent.find_one({
                    "reminder_key": reminder_key,
                })
                if already_sent:
                    continue

                # Send reminder
                sent = await _send_reminder(user, d, minutes_before)
                if sent:
                    await db.reminders_sent.insert_one({
                        "reminder_key": reminder_key,
                        "user_id": user_id,
                        "deadline_id": d["id"],
                        "minutes_before": minutes_before,
                        "sent_at": now,
                    })
                    total_sent += 1

    if total_sent:
        logger.info(f"Sent {total_sent} reminders")


async def _send_reminder(user: dict, deadline: dict, minutes_before: int) -> bool:
    """Send a single reminder via Telegram."""
    try:
        from telegram_bot.bot import get_bot_app
        bot_app = get_bot_app()
        if not bot_app:
            return False

        due_msk = deadline["due_date"] + timedelta(hours=3)
        date_str = due_msk.strftime("%d.%m %H:%M")

        if minutes_before >= 1440:
            hours = minutes_before // 60
            time_label = f"{hours} ч."
        elif minutes_before >= 60:
            hours = minutes_before // 60
            time_label = f"{hours} ч."
        else:
            time_label = f"{minutes_before} мин."

        text = (
            f"Напоминание: {deadline['name']} — {deadline['task']}\n"
            f"До дедлайна: {time_label}\n"
            f"Срок: {date_str} МСК"
        )

        await bot_app.bot.send_message(chat_id=user["telegram_id"], text=text)
        return True

    except Exception as e:
        logger.warning(f"Failed to send reminder to {user.get('telegram_id')}: {e}")
        return False
