import logging

from telegram_userbot.channel_manager import join_pending_channels

logger = logging.getLogger(__name__)


async def channel_join_job():
    """Periodically check for new sources that need joining."""
    logger.info("Running channel join job...")
    try:
        await join_pending_channels()
    except Exception as e:
        logger.error(f"Channel join job error: {e}")
