from pydantic import BaseModel, field_serializer
from typing import Optional
from datetime import datetime, timezone


class SourceCreate(BaseModel):
    type: str  # "telegram_channel" | "wiki_page"
    identifier: str  # @channel or URL
    display_name: Optional[str] = None


class Source(BaseModel):
    id: str
    user_id: str
    type: str
    identifier: str
    display_name: str
    is_active: bool = True
    joined: bool = False
    last_checked_at: Optional[datetime] = None
    last_post_id: Optional[int] = None
    last_content_hash: Optional[str] = None
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @field_serializer("last_checked_at", "created_at", "updated_at", when_used="json")
    def serialize_utc(self, value):
        return value.replace(tzinfo=timezone.utc) if value is not None and value.tzinfo is None else value
