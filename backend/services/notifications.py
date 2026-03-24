import logging
import os
from typing import List

from bson import ObjectId

from services.database import get_db

logger = logging.getLogger(__name__)


async def notify_new_deadlines(user_ids: List[str], deadlines: List[dict], source_name: str, count: int):
    """Send TG notification about new deadlines to users."""
    if count == 0:
        return

    try:
        from telegram_bot.bot import get_bot_app
        bot_app = get_bot_app()
        if not bot_app:
            return

        db = get_db()
        object_ids = [ObjectId(uid) for uid in user_ids]
        users = await db.users.find({"_id": {"$in": object_ids}}).to_list(len(user_ids))

        frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")

        lines = [f"📌 Новые дедлайны ({count} шт.) из {source_name}:\n"]
        for d in deadlines[:10]:
            due = d.get("due_date", "?")
            # Format date nicely if it's ISO
            if isinstance(due, str) and "T" in due:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(due)
                    due = dt.strftime("%d.%m %H:%M")
                except Exception:
                    pass
            lines.append(f"  • {d.get('task_name', '?')} — до {due}")

        if len(deadlines) > 10:
            lines.append(f"  ... и ещё {len(deadlines) - 10}")

        lines.append(f"\n📊 Дашборд: {frontend_url}?token={{token}}")

        for user in users:
            if not user.get("settings", {}).get("notifications_enabled", True):
                continue
            try:
                text = "\n".join(lines).replace("{token}", user["dashboard_token"])
                await bot_app.bot.send_message(chat_id=user["telegram_id"], text=text)
            except Exception as e:
                logger.warning(f"Failed to notify user {user['telegram_id']}: {e}")

    except Exception as e:
        logger.error(f"Notification error: {e}")
