import hashlib
import logging
import uuid
from datetime import datetime
from typing import List

from services.database import get_db

logger = logging.getLogger(__name__)


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


async def save_extracted_deadlines(
    user_ids: List[str],
    extracted: List[dict],
    source_id: str,
    source_type: str,
    raw_text: str,
) -> int:
    """Save extracted deadlines to DB for given users. Returns count of new deadlines."""
    db = get_db()
    c_hash = content_hash(raw_text)

    existing = await db.parsed_posts.find_one({
        "source_id": source_id,
        "content_hash": c_hash,
    })
    if existing:
        return 0

    await db.parsed_posts.insert_one({
        "source_id": source_id,
        "content_hash": c_hash,
        "raw_text": raw_text[:5000],
        "has_deadline": len(extracted) > 0,
        "extracted_deadlines": extracted,
        "processed_at": datetime.utcnow(),
    })

    # Prepare all valid deadlines
    docs_to_insert = []
    now = datetime.utcnow()

    for deadline_data in extracted:
        confidence = deadline_data.get("confidence", 0)
        if confidence < 0.6:
            continue

        due_date_str = deadline_data.get("due_date")
        if not due_date_str:
            continue

        try:
            due_date = datetime.fromisoformat(due_date_str)
        except (ValueError, TypeError):
            logger.warning(f"Cannot parse due_date: {due_date_str}")
            continue

        task_name = deadline_data.get("task_name", "Unknown")
        subject = deadline_data.get("subject", "Unknown")

        for user_id in user_ids:
            docs_to_insert.append({
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "name": subject,
                "task": task_name,
                "due_date": due_date,
                "created_at": now,
                "updated_at": now,
                "is_recurring": False,
                "interval_days": None,
                "last_started_at": None,
                "source": {
                    "type": source_type,
                    "source_id": source_id,
                    "original_text": raw_text[:1000],
                },
                "confidence": confidence,
                "is_postponed": False,
                "previous_due_date": None,
            })

    if not docs_to_insert:
        return 0

    # Batch dedup: fetch all existing (user_id, name, task, due_date) combos
    dedup_keys = [
        {"user_id": d["user_id"], "name": d["name"], "task": d["task"], "due_date": d["due_date"]}
        for d in docs_to_insert
    ]
    existing_deadlines = await db.deadlines.find(
        {"$or": dedup_keys},
        {"user_id": 1, "name": 1, "task": 1, "due_date": 1},
    ).to_list(len(dedup_keys))

    existing_set = {
        (d["user_id"], d["name"], d["task"], d["due_date"].isoformat() if hasattr(d["due_date"], "isoformat") else str(d["due_date"]))
        for d in existing_deadlines
    }

    new_docs = [
        d for d in docs_to_insert
        if (d["user_id"], d["name"], d["task"], d["due_date"].isoformat()) not in existing_set
    ]

    if new_docs:
        await db.deadlines.insert_many(new_docs)

    logger.info(f"Saved {len(new_docs)} new deadlines from source {source_id}")
    return len(new_docs)
