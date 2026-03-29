import logging
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from services.database import get_db
from telegram_bot.utils import get_current_user

logger = logging.getLogger(__name__)

SOURCE_ICONS = {"manual": "M", "telegram": "T", "wiki": "W"}
COMPLETE_DEADLINE_CB = "done_dl:"


def _channel_link(identifier: str) -> str | None:
    """Build t.me link from source identifier."""
    if not identifier:
        return None
    if identifier.startswith("@"):
        return f"https://t.me/{identifier[1:]}"
    return None


async def my_deadlines_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_current_user(update)
    if not user:
        return

    db = get_db()
    now = datetime.utcnow()
    user_id = str(user["_id"])

    deadlines = await db.deadlines.find({
        "user_id": user_id,
        "due_date": {"$gte": now},
    }).sort("due_date", 1).to_list(20)

    if not deadlines:
        msg = update.message or update.callback_query.message
        await msg.reply_text("Нет предстоящих дедлайнов!")
        return

    # Collect source_ids to fetch channel links
    source_ids = set()
    for d in deadlines:
        sid = d.get("source", {}).get("source_id")
        if sid:
            source_ids.add(sid)

    source_map = {}
    if source_ids:
        from bson import ObjectId
        oids = []
        for sid in source_ids:
            try:
                oids.append(ObjectId(sid))
            except Exception:
                pass
        if oids:
            sources = await db.sources.find({"_id": {"$in": oids}}).to_list(100)
            for s in sources:
                source_map[str(s["_id"])] = s

    lines = ["Ближайшие дедлайны:\n"]
    buttons = []
    for d in deadlines:
        due = d["due_date"]
        due_msk = due + timedelta(hours=3)
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

        date_str = due_msk.strftime("%d.%m %H:%M")
        confidence = d.get("confidence")
        conf_str = f" ({int(confidence * 100)}%)" if confidence else ""

        # Build channel link
        source_id = d.get("source", {}).get("source_id")
        source_doc = source_map.get(source_id)
        link = ""
        if source_doc:
            url = _channel_link(source_doc.get("identifier", ""))
            if url:
                link = f" | {url}"

        lines.append(
            f"[{icon}] {d['name']} — {d['task']}\n"
            f"   {date_str} (через {time_str}){conf_str}{link}"
        )

        # Complete button per deadline
        short_name = d['name'][:25]
        buttons.append([
            InlineKeyboardButton(
                f"\u2705 {short_name}",
                callback_data=f"{COMPLETE_DEADLINE_CB}{d['id']}",
            )
        ])

    keyboard = InlineKeyboardMarkup(buttons) if buttons else None
    msg = update.message or update.callback_query.message
    await msg.reply_text("\n".join(lines), reply_markup=keyboard, disable_web_page_preview=True)


async def complete_deadline_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle deadline completion via inline button."""
    query = update.callback_query
    await query.answer()

    deadline_id = query.data.removeprefix(COMPLETE_DEADLINE_CB)
    db = get_db()

    deadline = await db.deadlines.find_one({"id": deadline_id})
    if not deadline:
        await query.answer("Дедлайн не найден", show_alert=True)
        return

    await db.deadlines.delete_one({"id": deadline_id})

    # Record completion
    from datetime import datetime
    await db.completions.insert_one({
        "user_id": deadline.get("user_id", ""),
        "deadline_name": deadline.get("name", ""),
        "deadline_task": deadline.get("task", ""),
        "completed_at": datetime.utcnow(),
    })

    name = deadline.get("name", "")
    await query.answer(f"Выполнено: {name}")

    # Refresh the list
    await my_deadlines_command(update, context)
