import logging
import string
import random
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import ContextTypes

from services.database import get_db
from telegram_bot.utils import get_current_user

logger = logging.getLogger(__name__)


def _generate_code(length=6) -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=length))


async def share_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/share — generate a short code that others can use with /join."""
    user = await get_current_user(update)
    if not user:
        return

    db = get_db()
    user_id = str(user["_id"])

    sources = await db.sources.find({
        "user_id": user_id,
        "is_active": True,
    }).to_list(200)

    if not sources:
        await update.message.reply_text("У тебя нет источников для шаринга. Сначала добавь каналы или wiki.")
        return

    channels = [s["identifier"] for s in sources if s["type"] == "telegram_channel"]
    wikis = [s["identifier"] for s in sources if s["type"] == "wiki_page"]

    code = _generate_code()
    expires_at = datetime.utcnow() + timedelta(days=7)

    await db.share_codes.insert_one({
        "code": code,
        "created_by": user_id,
        "channels": channels,
        "wikis": wikis,
        "expires_at": expires_at,
        "created_at": datetime.utcnow(),
    })

    summary_lines = []
    if channels:
        summary_lines.append(f"Каналы: {', '.join(channels)}")
    if wikis:
        summary_lines.append(f"Wiki: {len(wikis)} шт.")
    summary = "\n".join(summary_lines)

    await update.message.reply_text(
        f"Код для одногруппников:\n\n"
        f"  /join {code}\n\n"
        f"Что включено:\n{summary}\n\n"
        f"Код действует 7 дней."
    )
    logger.info(f"User {update.effective_user.id} created share code {code}")


async def join_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/join ABCD — import sources from a share code."""
    user = await get_current_user(update)
    if not user:
        return

    if not context.args:
        await update.message.reply_text("Укажи код: /join ABCDEF")
        return

    code = context.args[0].strip().upper()
    db = get_db()

    share = await db.share_codes.find_one({
        "code": code,
        "expires_at": {"$gte": datetime.utcnow()},
    })

    if not share:
        await update.message.reply_text("Код не найден или истёк. Попроси одногруппника сгенерировать новый: /share")
        return

    user_id = str(user["_id"])
    now = datetime.utcnow()
    added = 0

    for channel in share.get("channels", []):
        existing = await db.sources.find_one({
            "user_id": user_id, "type": "telegram_channel", "identifier": channel,
        })
        if existing and existing.get("is_active"):
            continue
        if existing:
            await db.sources.update_one(
                {"_id": existing["_id"]},
                {"$set": {"is_active": True, "updated_at": now}},
            )
        else:
            await db.sources.insert_one({
                "user_id": user_id, "type": "telegram_channel",
                "identifier": channel, "display_name": channel,
                "is_active": True, "joined": False,
                "last_checked_at": None, "last_post_id": None,
                "last_content_hash": None,
                "created_at": now, "updated_at": now,
            })
        added += 1

    for url in share.get("wikis", []):
        existing = await db.sources.find_one({
            "user_id": user_id, "type": "wiki_page", "identifier": url,
        })
        if existing and existing.get("is_active"):
            continue
        if existing:
            await db.sources.update_one(
                {"_id": existing["_id"]},
                {"$set": {"is_active": True, "updated_at": now}},
            )
        else:
            await db.sources.insert_one({
                "user_id": user_id, "type": "wiki_page",
                "identifier": url,
                "display_name": url.split("/")[-1].replace("_", " "),
                "is_active": True, "joined": True,
                "last_checked_at": None, "last_post_id": None,
                "last_content_hash": None,
                "created_at": now, "updated_at": now,
            })
        added += 1

    await update.message.reply_text(f"Добавлено {added} источников! Дедлайны скоро появятся на дашборде.")
    logger.info(f"User {update.effective_user.id} joined with code {code}, added {added} sources")
