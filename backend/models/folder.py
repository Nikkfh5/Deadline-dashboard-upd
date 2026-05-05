from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class FolderCreate(BaseModel):
    name: str = Field(max_length=100)
    type: Literal["deadlines", "ideas"] = "deadlines"


class FolderUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)


class Folder(BaseModel):
    id: str
    user_id: str
    name: str
    type: str
    is_default: bool = False
    created_at: datetime
    updated_at: datetime
