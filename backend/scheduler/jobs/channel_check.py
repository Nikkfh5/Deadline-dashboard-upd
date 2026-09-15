import logging

from telegram_userbot.channel_manager import join_pending_channels

logger = logging.getLogger(__name__)


async def channel_join_job():
    """Periodically check for new sources that need joining."""
    logger.info("Running channel join job...")
    try:
        from telegram_userbot.client import get_userbot
        client = get_userbot()
        if client and not client.is_connected():
            logger.warning("Userbot disconnected, reconnecting...")
            await client.connect()
            await client.get_me()
            await client.catch_up()
            logger.info("Userbot reconnected, event handlers active")
        await join_pending_channels()
    except Exception as e:
        logger.error(f"Channel join job error: {e}")
