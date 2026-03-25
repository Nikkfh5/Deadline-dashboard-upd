import logging
from datetime import datetime
from typing import Optional

from telethon import TelegramClient
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest, CheckChatInviteRequest
from telethon.errors import (
    ChannelPrivateError,
    FloodWaitError,
    UserAlreadyParticipantError,
    InviteHashExpiredError,
    InviteHashInvalidError,
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
            if identifier.startswith("invite:"):
                # Private channel via invite link
                invite_hash = identifier[len("invite:"):]
                await _join_by_invite(client, db, source, invite_hash)
            else:
                # Public channel via @username
                channel = identifier.lstrip("@")
                entity = await client.get_entity(channel)
                await client(JoinChannelRequest(entity))

                await db.sources.update_one(
                    {"_id": source["_id"]},
                    {"$set": {
                        "joined": True,
                        "display_name": getattr(entity, "title", identifier),
                        "updated_at": datetime.utcnow(),
                    }},
                )
                logger.info(f"Joined public channel: {identifier} ({getattr(entity, 'title', '?')})")

        except UserAlreadyParticipantError:
            await _mark_joined(db, source, client, identifier)

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


async def _join_by_invite(client, db, source, invite_hash):
    """Join a private channel via invite hash."""
    try:
        # Try to join
        result = await client(ImportChatInviteRequest(invite_hash))
        chat = result.chats[0] if result.chats else None
        title = chat.title if chat else "Private channel"

        # Update source with real channel info
        update_fields = {
            "joined": True,
            "display_name": title,
            "updated_at": datetime.utcnow(),
        }
        # Store channel ID for matching incoming messages
        if chat:
            update_fields["channel_id"] = chat.id

        await db.sources.update_one({"_id": source["_id"]}, {"$set": update_fields})
        logger.info(f"Joined private channel via invite: {title} (hash: {invite_hash[:8]}...)")

    except UserAlreadyParticipantError:
        # Already joined — get channel info via CheckChatInvite
        try:
            info = await client(CheckChatInviteRequest(invite_hash))
            chat = getattr(info, "chat", None)
            title = chat.title if chat else "Private channel"
            update_fields = {
                "joined": True,
                "display_name": title,
                "updated_at": datetime.utcnow(),
            }
            if chat:
                update_fields["channel_id"] = chat.id
            await db.sources.update_one({"_id": source["_id"]}, {"$set": update_fields})
            logger.info(f"Already in private channel: {title}")
        except Exception:
            await db.sources.update_one(
                {"_id": source["_id"]},
                {"$set": {"joined": True, "updated_at": datetime.utcnow()}},
            )

    except (InviteHashExpiredError, InviteHashInvalidError):
        logger.warning(f"Invite link expired/invalid: {invite_hash[:8]}...")
        await db.sources.update_one(
            {"_id": source["_id"]},
            {"$set": {"is_active": False, "updated_at": datetime.utcnow()}},
        )


async def _mark_joined(db, source, client, identifier):
    """Mark source as joined and try to get the real channel title."""
    update_fields = {"joined": True, "updated_at": datetime.utcnow()}
    try:
        if not identifier.startswith("invite:"):
            entity = await client.get_entity(identifier.lstrip("@"))
            update_fields["display_name"] = getattr(entity, "title", identifier)
    except Exception:
        pass
    await db.sources.update_one({"_id": source["_id"]}, {"$set": update_fields})
    logger.info(f"Already in channel: {identifier}")
