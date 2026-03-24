import logging
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from services.database import get_db
from telegram_bot.utils import get_current_user

logger = logging.getLogger(__name__)


def _is_valid_wiki_url(url: str) -> bool:
    return url.startswith("http://wiki.cs.hse.ru/") or url.startswith("https://wiki.cs.hse.ru/")


async def add_wiki_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Укажи URL wiki-страницы:\n"
            "/add_wiki http://wiki.cs.hse.ru/..."
        )
        return

    url = context.args[0].strip()
    if not _is_valid_wiki_url(url):
        await update.message.reply_text(
            "Поддерживаются только страницы wiki.cs.hse.ru\n"
            "Пример: /add_wiki http://wiki.cs.hse.ru/Математический_Анализ_2"
        )
        return

    user = await get_current_user(update)
    if not user:
        return

    db = get_db()
    user_id = str(user["_id"])

    existing = await db.sources.find_one({
        "user_id": user_id,
        "type": "wiki_page",
        "identifier": url,
    })

    if existing and existing.get("is_active", True):
        await update.message.reply_text("Эта wiki-страница уже отслеживается.")
        return

    if existing:
        await db.sources.update_one(
            {"_id": existing["_id"]},
            {"$set": {"is_active": True, "updated_at": datetime.utcnow()}},
        )
    else:
        now = datetime.utcnow()
        await db.sources.insert_one({
            "user_id": user_id,
            "type": "wiki_page",
            "identifier": url,
            "display_name": url.split("/")[-1].replace("_", " "),
            "is_active": True,
            "joined": True,
            "last_checked_at": None,
            "last_post_id": None,
            "last_content_hash": None,
            "created_at": now,
            "updated_at": now,
        })

    await update.message.reply_text(
        "Wiki-страница добавлена!\n"
        "Бот будет проверять обновления каждый час."
    )
    logger.info(f"User {update.effective_user.id} added wiki {url}")


async def remove_wiki_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Укажи URL: /remove_wiki http://wiki.cs.hse.ru/...")
        return

    url = context.args[0].strip()
    user = await get_current_user(update)
    if not user:
        return

    db = get_db()
    result = await db.sources.update_one(
        {"user_id": str(user["_id"]), "type": "wiki_page", "identifier": url},
        {"$set": {"is_active": False, "updated_at": datetime.utcnow()}},
    )

    if result.modified_count == 0:
        await update.message.reply_text("Wiki-страница не найдена в твоих источниках.")
    else:
        await update.message.reply_text("Wiki-страница удалена из мониторинга.")


async def list_wikis_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_current_user(update)
    if not user:
        return

    db = get_db()
    sources = await db.sources.find({
        "user_id": str(user["_id"]),
        "type": "wiki_page",
        "is_active": True,
    }).to_list(100)

    if not sources:
        await update.message.reply_text(
            "У тебя нет отслеживаемых wiki-страниц.\n"
            "Добавь: /add_wiki http://wiki.cs.hse.ru/..."
        )
        return

    lines = ["Отслеживаемые wiki-страницы:\n"]
    for s in sources:
        name = s.get("display_name", s["identifier"])
        lines.append(f"- {name}")

    await update.message.reply_text("\n".join(lines))
