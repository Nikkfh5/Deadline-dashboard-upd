import hashlib
import logging
import uuid
from datetime import datetime
from difflib import SequenceMatcher
from typing import List, Tuple

from models.deadline import strip_html_tags
from services.database import get_db

logger = logging.getLogger(__name__)

DEDUPE_SIMILARITY_THRESHOLD = 0.6
MAX_RAW_TEXT_STORE = 5000
MAX_ORIGINAL_TEXT = 1000


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


async def save_extracted_deadlines(
    user_ids: List[str],
    extracted: List[dict],
    source_id: str,
    source_type: str,
    raw_text: str,
) -> Tuple[int, List[dict]]:
    """Save extracted deadlines to DB for given users.

    Returns (new_count, rescheduled_list) where rescheduled_list contains
    dicts like {"name": ..., "task": ..., "old_date": ..., "new_date": ...}.
    """
    db = get_db()
    c_hash = content_hash(raw_text)

    # Check if this text was already analyzed (by any source) — reuse cached result
    cached = await db.parsed_posts.find_one({"content_hash": c_hash})
    if cached:
        # Reuse cached Haiku result instead of the new extraction
        extracted = cached.get("extracted_deadlines", [])
        if not extracted:
            return 0, []
    else:
        await db.parsed_posts.insert_one({
            "source_id": source_id,
            "content_hash": c_hash,
            "raw_text": raw_text[:MAX_RAW_TEXT_STORE],
            "has_deadline": len(extracted) > 0,
            "extracted_deadlines": extracted,
            "processed_at": datetime.utcnow(),
        })

    # Prepare all valid deadlines
    docs_to_insert = []
    now = datetime.utcnow()

    for deadline_data in extracted:
        confidence = deadline_data.get("confidence", 0)
        if confidence < DEDUPE_SIMILARITY_THRESHOLD:
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
        details = deadline_data.get("details", "")
        # Combine task name with details for richer dashboard display
        task_display = f"{task_name} | {details}" if details else task_name

        for user_id in user_ids:
            docs_to_insert.append({
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "name": strip_html_tags(subject)[:500],
                "task": strip_html_tags(task_display)[:500],
                "due_date": due_date,
                "created_at": now,
                "updated_at": now,
                "is_recurring": False,
                "interval_days": None,
                "last_started_at": None,
                "source": {
                    "type": source_type,
                    "source_id": source_id,
                    "original_text": raw_text[:MAX_ORIGINAL_TEXT],
                },
                "confidence": confidence,
                "is_postponed": False,
                "previous_due_date": None,
            })

    if not docs_to_insert:
        return 0, []

    # Batch dedup: fetch existing deadlines by (user_id, name) for fuzzy matching
    dedup_keys = [
        {"user_id": d["user_id"], "name": d["name"]}
        for d in docs_to_insert
    ]
    # Deduplicate the query keys
    seen_keys = set()
    unique_dedup_keys = []
    for k in dedup_keys:
        key_tuple = (k["user_id"], k["name"])
        if key_tuple not in seen_keys:
            seen_keys.add(key_tuple)
            unique_dedup_keys.append(k)

    existing_deadlines = await db.deadlines.find(
        {"$or": unique_dedup_keys},
        {"user_id": 1, "name": 1, "task": 1, "due_date": 1, "_id": 1},
    ).to_list(1000)

    # Group existing deadlines by (user_id, name) for fast lookup
    from collections import defaultdict
    existing_by_user_name = defaultdict(list)
    for ed in existing_deadlines:
        existing_by_user_name[(ed["user_id"], ed["name"])].append(ed)

    new_docs = []
    rescheduled = []
    now = datetime.utcnow()

    for doc in docs_to_insert:
        candidates = existing_by_user_name.get((doc["user_id"], doc["name"]), [])
        matched = False

        for existing in candidates:
            ratio = SequenceMatcher(None, existing["task"], doc["task"]).ratio()
            if ratio >= DEDUPE_SIMILARITY_THRESHOLD:
                # Fuzzy match found
                existing_due = existing["due_date"]
                new_due = doc["due_date"]
                if existing_due != new_due:
                    # Reschedule: update existing deadline
                    await db.deadlines.update_one(
                        {"_id": existing["_id"]},
                        {"$set": {
                            "due_date": new_due,
                            "previous_due_date": existing_due,
                            "is_postponed": True,
                            "updated_at": now,
                            "task": doc["task"],
                        }},
                    )
                    rescheduled.append({
                        "name": doc["name"],
                        "task": doc["task"],
                        "old_date": existing_due,
                        "new_date": new_due,
                    })
                # else: same date, near-duplicate -> skip
                matched = True
                break

        # Intra-batch dedup: check against docs already accepted in this batch
        if not matched:
            for accepted in new_docs:
                if accepted["user_id"] == doc["user_id"] and accepted["name"] == doc["name"]:
                    ratio = SequenceMatcher(None, accepted["task"], doc["task"]).ratio()
                    if ratio >= DEDUPE_SIMILARITY_THRESHOLD:
                        matched = True
                        break

        if not matched:
            new_docs.append(doc)

    if new_docs:
        await db.deadlines.insert_many(new_docs)

    logger.info(
        f"Saved {len(new_docs)} new deadlines, "
        f"{len(rescheduled)} rescheduled from source {source_id}"
    )
    return len(new_docs), rescheduled
