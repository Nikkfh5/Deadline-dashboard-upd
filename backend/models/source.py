from pydantic import BaseModel
from typing import Optional
from datetime import datetime


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
    created_at: datetime
    updated_at: datetime
