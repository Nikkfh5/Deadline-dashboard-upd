import logging
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from services.database import get_db
from telegram_bot.utils import get_current_user

logger = logging.getLogger(__name__)

WAITING_WIKI_URL = 0

_REPLY_BUTTONS = frozenset({
    "Добавить дедлайн", "Добавить канал", "Добавить wiki",
    "Мои дедлайны", "Мои источники", "Настройки",
})
_TEXT_INPUT = filters.TEXT & ~filters.COMMAND & ~filters.Text(_REPLY_BUTTONS)
DEL_WIKI_CB = "del_wiki:"


def _is_valid_wiki_url(url: str) -> bool:
    return url.startswith("http://wiki.cs.hse.ru/") or url.startswith("https://wiki.cs.hse.ru/")


async def add_wiki_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = await get_current_user(update)
    if not user:
        return ConversationHandler.END

    if context.args:
        await _process_wiki_url(update, context.args[0].strip(), user)
        return ConversationHandler.END

    context.user_data["add_wiki_user"] = user
    await update.message.reply_text("Отправь ссылку на wiki-страницу:")
    return WAITING_WIKI_URL


async def wiki_url_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = context.user_data.pop("add_wiki_user", None)
    if not user:
        user = await get_current_user(update)
        if not user:
            return ConversationHandler.END

    await _process_wiki_url(update, update.message.text.strip(), user)
    return ConversationHandler.END


async def _process_wiki_url(update, url: str, user: dict):
    if not _is_valid_wiki_url(url):
        await update.message.reply_text(
            "Поддерживаются только страницы wiki.cs.hse.ru\n"
            "Пример: http://wiki.cs.hse.ru/Математический_Анализ_2"
        )
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


def build_add_wiki_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("add_wiki", add_wiki_command),
            MessageHandler(filters.Text(["Добавить wiki"]), add_wiki_command),
        ],
        states={
            WAITING_WIKI_URL: [
                MessageHandler(_TEXT_INPUT, wiki_url_received),
            ],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
        allow_reentry=True,
        conversation_timeout=120,
        per_user=True,
        per_chat=True,
    )


async def remove_wiki_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show wikis as buttons for deletion."""
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
        await update.message.reply_text("Нет wiki для удаления.")
        return

    buttons = []
    for s in sources:
        name = s.get("display_name", s["identifier"])
        buttons.append([InlineKeyboardButton(
            f"X  {name}",
            callback_data=f"{DEL_WIKI_CB}{s['_id']}",
        )])

    await update.message.reply_text(
        "Нажми на wiki чтобы удалить:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def delete_wiki_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle wiki deletion via inline button."""
    query = update.callback_query
    await query.answer()

    from bson import ObjectId
    source_id = query.data.removeprefix(DEL_WIKI_CB)

    db = get_db()
    source = await db.sources.find_one({"_id": ObjectId(source_id)})
    if not source:
        await query.answer("Wiki не найдена", show_alert=True)
        return

    await db.sources.delete_one({"_id": ObjectId(source_id)})
    name = source.get("display_name", source["identifier"])
    await query.edit_message_text(f"Wiki \"{name}\" удалена.")


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

    msg = update.message or update.callback_query.message

    if not sources:
        await msg.reply_text("Нет отслеживаемых wiki-страниц.")
        return

    lines = ["<b>Отслеживаемые wiki:</b>\n"]
    for s in sources:
        name = s.get("display_name", s["identifier"])
        url = s.get("identifier", "")
        if url.startswith("http"):
            lines.append(f'📄 <a href="{url}">{name}</a>')
        else:
            lines.append(f"📄 {name}")

    await msg.reply_text("\n".join(lines), parse_mode="HTML", disable_web_page_preview=True)
