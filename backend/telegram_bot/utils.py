from telegram import Update
from services.database import get_db


async def get_current_user(update: Update):
    """Get user doc by telegram_id. Returns None and sends prompt if not found."""
    db = get_db()
    user = await db.users.find_one({"telegram_id": update.effective_user.id})
    if not user:
        await update.message.reply_text("Сначала запусти бота: /start")
        return None
    return user
