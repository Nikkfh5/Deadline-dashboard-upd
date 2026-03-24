from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ExtractedDeadline(BaseModel):
    task_name: str
    subject: str
    due_date: str  # ISO8601
    confidence: float


class ParsedPost(BaseModel):
    id: str
    source_id: str
    content_hash: str
    raw_text: str
    has_deadline: bool
    extracted_deadlines: List[ExtractedDeadline] = []
    processed_at: datetime
