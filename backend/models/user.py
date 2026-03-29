from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class UserSettings(BaseModel):
    check_interval_minutes: int = 60
    timezone: str = "Europe/Moscow"
    notifications_enabled: bool = True
    reminder_minutes: List[int] = [1440, 60]


class UserCreate(BaseModel):
    telegram_id: int
    telegram_username: Optional[str] = None
    first_name: str


class User(BaseModel):
    id: str
    telegram_id: int
    telegram_username: Optional[str] = None
    first_name: str
    dashboard_token: str
    settings: UserSettings = UserSettings()
    created_at: datetime
    updated_at: datetime
