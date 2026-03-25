import json
import logging
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from services.database import get_db
from telegram_bot.utils import get_current_user

logger = logging.getLogger(__name__)


async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Export all user sources as JSON for backup/sharing."""
    user = await get_current_user(update)
    if not user:
        return

    db = get_db()
    sources = await db.sources.find({
        "user_id": str(user["_id"]),
        "is_active": True,
    }).to_list(200)

    export_data = {
        "channels": [],
        "wikis": [],
    }
    for s in sources:
        if s["type"] == "telegram_channel":
            export_data["channels"].append(s["identifier"])
        elif s["type"] == "wiki_page":
            export_data["wikis"].append(s["identifier"])

    text = json.dumps(export_data, ensure_ascii=False, indent=2)

    await update.message.reply_text(
        f"Твои настройки:\n\n```\n{text}\n```\n\n"
        f"Скопируй и отправь другому человеку, "
        f"он сможет импортировать через /import",
        parse_mode="Markdown",
    )


async def import_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Import sources from JSON. Usage: /import {json}"""
    user = await get_current_user(update)
    if not user:
        return

    # Get text after /import
    raw = update.message.text
    json_start = raw.find("{")
    if json_start == -1:
        await update.message.reply_text(
            "Отправь JSON после команды:\n"
            '/import {"channels": ["@channel1"], "wikis": ["http://wiki.cs.hse.ru/..."]}'
        )
        return

    try:
        data = json.loads(raw[json_start:])
    except json.JSONDecodeError:
        await update.message.reply_text("Невалидный JSON. Проверь формат.")
        return

    db = get_db()
    user_id = str(user["_id"])
    now = datetime.utcnow()
    added = 0

    for channel in data.get("channels", []):
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

    for url in data.get("wikis", []):
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

    await update.message.reply_text(f"Импортировано {added} источников.")
    logger.info(f"User {update.effective_user.id} imported {added} sources")
