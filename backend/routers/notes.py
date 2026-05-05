from fastapi import APIRouter, HTTPException, Query
from typing import List
from datetime import datetime
import uuid

from models.note import Note, NoteCreate, NoteUpdate, NoteReorderItem
from services.database import get_db
from services.auth import get_user_by_token

router = APIRouter(prefix="/api/notes", tags=["notes"])


def _note_from_doc(doc: dict) -> Note:
    return Note(
        id=doc["id"],
        user_id=str(doc.get("user_id", "")),
        folder_id=doc["folder_id"],
        title=doc.get("title"),
        content=doc.get("content", ""),
        order=doc.get("order", 0),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


@router.get("", response_model=List[Note])
async def get_notes(token: str = Query(...), folder_id: str = Query(...)):
    user = await get_user_by_token(token)
    db = get_db()
    user_id = str(user["_id"])

    # Verify folder belongs to user
    folder = await db.folders.find_one({"id": folder_id, "user_id": user_id})
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    docs = await db.notes.find(
        {"user_id": user_id, "folder_id": folder_id}
    ).sort("order", 1).to_list(500)
    return [_note_from_doc(doc) for doc in docs]


@router.post("", response_model=Note)
async def create_note(data: NoteCreate, token: str = Query(...)):
    user = await get_user_by_token(token)
    db = get_db()
    user_id = str(user["_id"])

    # Verify folder belongs to user
    folder = await db.folders.find_one({"id": data.folder_id, "user_id": user_id})
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    # Assign order = max existing order + 1
    last = await db.notes.find_one(
        {"user_id": user_id, "folder_id": data.folder_id},
        sort=[("order", -1)],
    )
    order = (last["order"] + 1) if last else 0

    now = datetime.utcnow()
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "folder_id": data.folder_id,
        "title": data.title,
        "content": data.content,
        "order": order,
        "created_at": now,
        "updated_at": now,
    }
    await db.notes.insert_one(doc)
    return _note_from_doc(doc)


@router.put("/reorder")
async def reorder_notes(items: List[NoteReorderItem], token: str = Query(...)):
    user = await get_user_by_token(token)
    db = get_db()
    user_id = str(user["_id"])

    for item in items:
        await db.notes.update_one(
            {"id": item.id, "user_id": user_id},
            {"$set": {"order": item.order, "updated_at": datetime.utcnow()}},
        )
    return {"updated": len(items)}


@router.put("/{note_id}", response_model=Note)
async def update_note(note_id: str, data: NoteUpdate, token: str = Query(...)):
    user = await get_user_by_token(token)
    db = get_db()
    user_id = str(user["_id"])

    update = {"updated_at": datetime.utcnow()}
    for field, value in data.model_dump(exclude_unset=True).items():
        update[field] = value

    from pymongo import ReturnDocument
    result = await db.notes.find_one_and_update(
        {"id": note_id, "user_id": user_id},
        {"$set": update},
        return_document=ReturnDocument.AFTER,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Note not found")
    return _note_from_doc(result)


@router.delete("/{note_id}")
async def delete_note(note_id: str, token: str = Query(...)):
    user = await get_user_by_token(token)
    db = get_db()
    user_id = str(user["_id"])

    result = await db.notes.delete_one({"id": note_id, "user_id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"deleted": True}
