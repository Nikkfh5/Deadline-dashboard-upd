from fastapi import APIRouter, HTTPException, Query
from typing import List
from datetime import datetime
import uuid

from models.deadline import Deadline, DeadlineCreate, DeadlineUpdate, DeadlineSource
from services.database import get_db
from services.auth import get_user_by_token

router = APIRouter(prefix="/api/deadlines", tags=["deadlines"])


def _deadline_from_doc(doc: dict) -> Deadline:
    return Deadline(
        id=doc["id"],
        user_id=str(doc.get("user_id", "")),
        name=doc["name"],
        task=doc["task"],
        due_date=doc["due_date"],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
        is_recurring=doc.get("is_recurring", False),
        interval_days=doc.get("interval_days"),
        last_started_at=doc.get("last_started_at"),
        days_needed=doc.get("days_needed"),
        source=DeadlineSource(**doc.get("source", {"type": "manual"})),
        confidence=doc.get("confidence"),
        is_postponed=doc.get("is_postponed", False),
        previous_due_date=doc.get("previous_due_date"),
    )


@router.get("", response_model=List[Deadline])
async def get_deadlines(token: str = Query(...), skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)):
    user = await get_user_by_token(token)
    db = get_db()
    docs = await db.deadlines.find({"user_id": str(user["_id"])}).skip(skip).limit(limit).to_list(limit)
    return [_deadline_from_doc(doc) for doc in docs]


@router.post("", response_model=Deadline)
async def create_deadline(data: DeadlineCreate, token: str = Query(...)):
    user = await get_user_by_token(token)
    db = get_db()
    now = datetime.utcnow()
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": str(user["_id"]),
        "name": data.name,
        "task": data.task,
        "due_date": data.due_date,
        "created_at": now,
        "updated_at": now,
        "is_recurring": data.is_recurring,
        "interval_days": data.interval_days,
        "last_started_at": data.last_started_at,
        "days_needed": data.days_needed,
        "source": data.source.model_dump(),
        "confidence": None,
        "is_postponed": False,
        "previous_due_date": None,
    }
    await db.deadlines.insert_one(doc)
    return _deadline_from_doc(doc)


@router.put("/{deadline_id}", response_model=Deadline)
async def update_deadline(deadline_id: str, data: DeadlineUpdate, token: str = Query(...)):
    user = await get_user_by_token(token)
    db = get_db()
    update_fields = {"updated_at": datetime.utcnow()}
    for field, value in data.model_dump(exclude_unset=True).items():
        update_fields[field] = value

    from pymongo import ReturnDocument
    result = await db.deadlines.find_one_and_update(
        {"id": deadline_id, "user_id": str(user["_id"])},
        {"$set": update_fields},
        return_document=ReturnDocument.AFTER,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Deadline not found")
    return _deadline_from_doc(result)


@router.delete("/{deadline_id}")
async def delete_deadline(
    deadline_id: str,
    token: str = Query(...),
    complete: bool = Query(False),
):
    user = await get_user_by_token(token)
    db = get_db()
    user_id = str(user["_id"])

    deadline = await db.deadlines.find_one({"id": deadline_id, "user_id": user_id})
    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")

    await db.deadlines.delete_one({"id": deadline_id, "user_id": user_id})

    # Track deletion so auto-import won't re-create this deadline
    source = deadline.get("source", {})
    if source.get("type") in ("telegram", "wiki"):
        await db.deleted_deadlines.update_one(
            {"user_id": user_id, "name": deadline["name"]},
            {"$set": {
                "user_id": user_id,
                "name": deadline["name"],
                "task": deadline.get("task", ""),
                "deleted_at": datetime.utcnow(),
            }},
            upsert=True,
        )

    if complete:
        await db.completions.insert_one({
            "user_id": user_id,
            "deadline_name": deadline.get("name", ""),
            "deadline_task": deadline.get("task", ""),
            "completed_at": datetime.utcnow(),
        })

    return {"deleted": True, "completed": complete}
