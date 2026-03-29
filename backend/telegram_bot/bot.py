import logging
import os
from typing import Optional

from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

from telegram_bot.handlers.start import start_command, help_command, dashboard_command, reply_keyboard_handler, REPLY_KEYBOARD
from telegram_bot.handlers.channels import remove_channel_command, list_channels_command, build_add_channel_conversation, delete_channel_button, DEL_CHANNEL_CB
from telegram_bot.handlers.wiki import remove_wiki_command, list_wikis_command, build_add_wiki_conversation, delete_wiki_button, DEL_WIKI_CB
from telegram_bot.handlers.deadlines import my_deadlines_command, complete_deadline_button, COMPLETE_DEADLINE_CB
from telegram_bot.handlers.settings import share_command, join_command
from telegram_bot.handlers.user_settings import settings_command, settings_callback, custom_reminder_input, SETTINGS_CB
from telegram_bot.handlers.add_deadline import build_add_deadline_conversation

logger = logging.getLogger(__name__)

_app: Optional[Application] = None


async def start_bot():
    global _app
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN not set, bot disabled")
        return

    _app = Application.builder().token(token).build()

    _app.add_handler(build_add_deadline_conversation())
    _app.add_handler(build_add_channel_conversation())
    _app.add_handler(build_add_wiki_conversation())
    _app.add_handler(CommandHandler("start", start_command))
    _app.add_handler(CommandHandler("help", help_command))
    _app.add_handler(CommandHandler("dashboard", dashboard_command))
    _app.add_handler(CommandHandler("remove_channel", remove_channel_command))
    _app.add_handler(CommandHandler("list_channels", list_channels_command))
    _app.add_handler(CommandHandler("remove_wiki", remove_wiki_command))
    _app.add_handler(CommandHandler("list_wikis", list_wikis_command))
    _app.add_handler(CommandHandler("my_deadlines", my_deadlines_command))
    _app.add_handler(CommandHandler("share", share_command))
    _app.add_handler(CommandHandler("join", join_command))
    _app.add_handler(CommandHandler("settings", settings_command))
    _app.add_handler(CallbackQueryHandler(settings_callback, pattern=f"^{SETTINGS_CB}"))
    _app.add_handler(CallbackQueryHandler(complete_deadline_button, pattern=f"^{COMPLETE_DEADLINE_CB}"))
    _app.add_handler(CallbackQueryHandler(delete_channel_button, pattern=f"^{DEL_CHANNEL_CB}"))
    _app.add_handler(CallbackQueryHandler(delete_wiki_button, pattern=f"^{DEL_WIKI_CB}"))

    # Custom reminder number input (only fires if awaiting_custom_reminder is set)
    _app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r"^\d+$"),
        custom_reminder_input,
    ), group=1)

    # Reply keyboard buttons — must be LAST to not intercept conversation text
    KEYBOARD_TEXTS = {"Мои дедлайны", "Мои источники", "Дашборд", "Настройки"}
    _app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(f"^({'|'.join(KEYBOARD_TEXTS)})$"),
        reply_keyboard_handler,
    ))

    await _app.initialize()
    await _app.start()
    await _app.updater.start_polling(drop_pending_updates=True)

    await _app.bot.set_my_commands([
        ("add", "Добавить дедлайн"),
        ("my_deadlines", "Мои дедлайны"),
        ("add_channel", "Добавить TG канал"),
        ("add_wiki", "Добавить wiki"),
        ("remove_channel", "Удалить канал"),
        ("remove_wiki", "Удалить wiki"),
        ("dashboard", "Открыть дашборд"),
        ("settings", "Настройки"),
        ("share", "Поделиться источниками"),
        ("help", "Помощь"),
    ])

    logger.info("Telegram bot started")


async def stop_bot():
    global _app
    if _app:
        await _app.updater.stop()
        await _app.stop()
        await _app.shutdown()
        _app = None
        logger.info("Telegram bot stopped")


def get_bot_app() -> Optional[Application]:
    return _app
