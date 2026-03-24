import logging
from datetime import datetime
from typing import Optional

from telethon import TelegramClient
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import (
    ChannelPrivateError,
    FloodWaitError,
    UserAlreadyParticipantError,
)

from services.database import get_db

logger = logging.getLogger(__name__)


async def join_pending_channels(client: Optional[TelegramClient] = None):
    """Join channels that have joined=False in the sources collection."""
    if not client:
        from telegram_userbot.client import get_userbot
        client = get_userbot()

    if not client:
        return

    db = get_db()
    pending = await db.sources.find({
        "type": "telegram_channel",
        "is_active": True,
        "joined": False,
    }).to_list(50)

    for source in pending:
        identifier = source["identifier"]
        try:
            # Remove @ prefix for Telethon
            channel = identifier.lstrip("@")
            entity = await client.get_entity(channel)
            await client(JoinChannelRequest(entity))

            await db.sources.update_one(
                {"_id": source["_id"]},
                {"$set": {"joined": True, "updated_at": datetime.utcnow()}},
            )
            logger.info(f"Joined channel: {identifier}")

        except UserAlreadyParticipantError:
            await db.sources.update_one(
                {"_id": source["_id"]},
                {"$set": {"joined": True, "updated_at": datetime.utcnow()}},
            )
            logger.info(f"Already in channel: {identifier}")

        except ChannelPrivateError:
            logger.warning(f"Channel is private, cannot join: {identifier}")
            await db.sources.update_one(
                {"_id": source["_id"]},
                {"$set": {"is_active": False, "updated_at": datetime.utcnow()}},
            )

        except FloodWaitError as e:
            logger.warning(f"Flood wait {e.seconds}s for channel: {identifier}")
            break

        except Exception as e:
            logger.error(f"Failed to join channel {identifier}: {e}")
