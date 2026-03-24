import logging
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from services.database import get_db
from telegram_bot.utils import get_current_user

logger = logging.getLogger(__name__)

SOURCE_ICONS = {"manual": "M", "telegram": "T", "wiki": "W"}


async def my_deadlines_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_current_user(update)
    if not user:
        return

    db = get_db()
    now = datetime.utcnow()
    deadlines = await db.deadlines.find({
        "user_id": str(user["_id"]),
        "due_date": {"$gte": now},
    }).sort("due_date", 1).to_list(20)

    if not deadlines:
        await update.message.reply_text("Нет предстоящих дедлайнов!")
        return

    lines = ["Ближайшие дедлайны:\n"]
    for d in deadlines:
        due = d["due_date"]
        diff = due - now
        days = diff.days
        hours = diff.seconds // 3600

        source_type = d.get("source", {}).get("type", "manual")
        icon = SOURCE_ICONS.get(source_type, "?")

        if days > 0:
            time_str = f"{days}д {hours}ч"
        elif hours > 0:
            minutes = (diff.seconds % 3600) // 60
            time_str = f"{hours}ч {minutes}мин"
        else:
            minutes = diff.seconds // 60
            time_str = f"{minutes}мин"

        date_str = due.strftime("%d.%m %H:%M")
        confidence = d.get("confidence")
        conf_str = f" ({int(confidence * 100)}%)" if confidence else ""

        lines.append(
            f"[{icon}] {d['name']} -- {d['task']}\n"
            f"   {date_str} (через {time_str}){conf_str}"
        )

    await update.message.reply_text("\n".join(lines))
