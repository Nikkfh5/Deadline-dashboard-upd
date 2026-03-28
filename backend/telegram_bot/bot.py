import logging
import os
from typing import Optional

from telegram.ext import Application, CommandHandler, CallbackQueryHandler

from telegram_bot.handlers.start import start_command, help_command, dashboard_command, menu_button_handler, MENU_CB
from telegram_bot.handlers.channels import remove_channel_command, list_channels_command, build_add_channel_conversation
from telegram_bot.handlers.wiki import remove_wiki_command, list_wikis_command, build_add_wiki_conversation
from telegram_bot.handlers.deadlines import my_deadlines_command
from telegram_bot.handlers.settings import share_command, join_command
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
    _app.add_handler(CallbackQueryHandler(menu_button_handler, pattern=f"^{MENU_CB}"))

    await _app.initialize()
    await _app.start()
    await _app.updater.start_polling(drop_pending_updates=True)
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
