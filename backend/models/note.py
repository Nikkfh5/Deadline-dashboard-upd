import re
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime


def strip_html_tags(value: str) -> str:
    return re.sub(r'<[^>]+>', '', value).strip()


class NoteCreate(BaseModel):
    folder_id: str
    title: Optional[str] = Field(default=None, max_length=200)
    content: str = Field(default="", max_length=10000)

    @field_validator('title', 'content', mode='before')
    @classmethod
    def sanitize_strings(cls, v):
        if isinstance(v, str):
            return strip_html_tags(v)
        return v


class NoteUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    content: Optional[str] = Field(default=None, max_length=10000)
    order: Optional[int] = None

    @field_validator('title', 'content', mode='before')
    @classmethod
    def sanitize_strings(cls, v):
        if isinstance(v, str):
            return strip_html_tags(v)
        return v


class NoteReorderItem(BaseModel):
    id: str
    order: int


class Note(BaseModel):
    id: str
    user_id: str
    folder_id: str
    title: Optional[str] = None
    content: str
    order: int
    created_at: datetime
    updated_at: datetime
