from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from datetime import datetime
import os
import uuid

from models.user import User, UserCreate, UserSettings
from services.database import get_db

router = APIRouter(prefix="/api/users", tags=["users"])

# Internal API key for bot-to-backend calls
INTERNAL_API_KEY = os.environ.get("INTERNAL_API_KEY", "")


def _user_from_doc(doc: dict) -> User:
    return User(
        id=str(doc["_id"]),
        telegram_id=doc["telegram_id"],
        telegram_username=doc.get("telegram_username"),
        first_name=doc["first_name"],
        dashboard_token=doc["dashboard_token"],
        settings=UserSettings(**doc.get("settings", {})),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


@router.post("/register", response_model=User)
async def register_user(data: UserCreate):
    """Called by the TG bot internally. Returns full user with token."""
    db = get_db()
    existing = await db.users.find_one({"telegram_id": data.telegram_id})
    if existing:
        return _user_from_doc(existing)

    now = datetime.utcnow()
    doc = {
        "telegram_id": data.telegram_id,
        "telegram_username": data.telegram_username,
        "first_name": data.first_name,
        "dashboard_token": str(uuid.uuid4()),
        "settings": UserSettings().model_dump(),
        "created_at": now,
        "updated_at": now,
    }
    result = await db.users.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _user_from_doc(doc)


class UserPublic(UserCreate):
    """Public user info without sensitive fields like dashboard_token."""
    id: str
    first_name: str
    created_at: datetime


@router.get("/by-telegram/{telegram_id}", response_model=UserPublic)
async def get_user_by_telegram(telegram_id: int):
    """Public endpoint — returns user info WITHOUT dashboard_token."""
    db = get_db()
    doc = await db.users.find_one({"telegram_id": telegram_id})
    if not doc:
        raise HTTPException(status_code=404, detail="User not found")
    return UserPublic(
        id=str(doc["_id"]),
        telegram_id=doc["telegram_id"],
        telegram_username=doc.get("telegram_username"),
        first_name=doc["first_name"],
        created_at=doc["created_at"],
    )
