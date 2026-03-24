from fastapi import HTTPException
from services.database import get_db


async def get_user_by_token(token: str):
    """Shared token-based auth. Returns user doc or raises 401."""
    db = get_db()
    user = await db.users.find_one({"dashboard_token": token})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user
