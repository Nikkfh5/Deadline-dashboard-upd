from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DeadlineSource(BaseModel):
    type: str = "manual"  # "manual" | "telegram" | "wiki"
    source_id: Optional[str] = None
    original_text: Optional[str] = None


class DeadlineCreate(BaseModel):
    name: str
    task: str
    due_date: datetime
    is_recurring: bool = False
    interval_days: Optional[int] = None
    last_started_at: Optional[datetime] = None
    source: DeadlineSource = DeadlineSource()


class DeadlineUpdate(BaseModel):
    name: Optional[str] = None
    task: Optional[str] = None
    due_date: Optional[datetime] = None
    is_recurring: Optional[bool] = None
    interval_days: Optional[int] = None
    last_started_at: Optional[datetime] = None
    is_postponed: Optional[bool] = None
    previous_due_date: Optional[datetime] = None


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
    source: DeadlineSource = DeadlineSource()
    confidence: Optional[float] = None
    is_postponed: bool = False
    previous_due_date: Optional[datetime] = None
