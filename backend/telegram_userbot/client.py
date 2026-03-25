import logging
import os
from typing import Optional

from telethon import TelegramClient
from telethon.sessions import StringSession

logger = logging.getLogger(__name__)

_client: Optional[TelegramClient] = None


async def start_userbot() -> Optional[TelegramClient]:
    global _client
    api_id = os.environ.get("TELEGRAM_API_ID")
    api_hash = os.environ.get("TELEGRAM_API_HASH")
    session_string = os.environ.get("TELEGRAM_SESSION_STRING")

    if not all([api_id, api_hash, session_string]):
        logger.warning("Telethon credentials not set, userbot disabled")
        return None

    _client = TelegramClient(
        StringSession(session_string),
        int(api_id),
        api_hash,
    )

    await _client.start()
    me = await _client.get_me()
    logger.info(f"Telethon userbot started as {me.first_name} (ID: {me.id})")

    # Register event handlers
    from telegram_userbot.monitor import setup_handlers
    setup_handlers(_client)

    # Explicitly tell Telethon to start receiving updates
    # Without this, event handlers won't fire when running inside uvicorn
    await _client.catch_up()
    logger.info("Telethon catch_up complete, event handlers active")

    return _client


async def stop_userbot():
    global _client
    if _client:
        await _client.disconnect()
        _client = None
        logger.info("Telethon userbot stopped")


def get_userbot() -> Optional[TelegramClient]:
    return _client
