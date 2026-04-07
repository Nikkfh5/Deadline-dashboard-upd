import re
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


def strip_html_tags(value: str) -> str:
    """Remove HTML tags from string to prevent stored XSS."""
    return re.sub(r'<[^>]+>', '', value).strip()


class DeadlineSource(BaseModel):
    type: str = "manual"  # "manual" | "telegram" | "wiki"
    source_id: Optional[str] = None
    original_text: Optional[str] = None


class DeadlineCreate(BaseModel):
    name: str = Field(max_length=500)
    task: str = Field(max_length=500)
    due_date: datetime
    is_recurring: bool = False
    interval_days: Optional[int] = None
    last_started_at: Optional[datetime] = None
    days_needed: Optional[int] = Field(default=None, ge=1)
    source: DeadlineSource = DeadlineSource()

    @field_validator('name', 'task', mode='before')
    @classmethod
    def sanitize_strings(cls, v):
        if isinstance(v, str):
            return strip_html_tags(v)
        return v


class DeadlineUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=500)
    task: Optional[str] = Field(default=None, max_length=500)
    due_date: Optional[datetime] = None
    is_recurring: Optional[bool] = None
    interval_days: Optional[int] = None
    last_started_at: Optional[datetime] = None
    days_needed: Optional[int] = Field(default=None, ge=1)
    is_postponed: Optional[bool] = None
    previous_due_date: Optional[datetime] = None

    @field_validator('name', 'task', mode='before')
    @classmethod
    def sanitize_strings(cls, v):
        if isinstance(v, str):
            return strip_html_tags(v)
        return v


class Deadline(BaseModel):
    id: str
    user_id: Optional[str] = None
    name: str
    task: str
    due_date: datetime
    created_at: datetime
    updated_at: datetime
    is_recurring: bool = False
    interval_days: Optional[int] = None
    last_started_at: Optional[datetime] = None
    days_needed: Optional[int] = None
    source: DeadlineSource = DeadlineSource()
    confidence: Optional[float] = None
    is_postponed: bool = False
    previous_due_date: Optional[datetime] = None
