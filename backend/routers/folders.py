from fastapi import APIRouter, HTTPException, Query
from typing import List
from datetime import datetime
import uuid

from models.folder import Folder, FolderCreate, FolderUpdate
from services.database import get_db
from services.auth import get_user_by_token

router = APIRouter(prefix="/api/folders", tags=["folders"])

DEFAULT_FOLDERS = [
    {"name": "Deadlines", "type": "deadlines", "is_default": True},
    {"name": "Ideas", "type": "ideas", "is_default": False},
]


def _folder_from_doc(doc: dict) -> Folder:
    return Folder(
        id=doc["id"],
        user_id=str(doc.get("user_id", "")),
        name=doc["name"],
        type=doc["type"],
        is_default=doc.get("is_default", False),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def _ensure_default_folders(db, user_id: str) -> List[dict]:
    """Create default folders for a user if none exist. Returns all folders."""
    existing = await db.folders.find({"user_id": user_id}).to_list(100)
    if existing:
        return existing

    now = datetime.utcnow()
    docs = []
    for template in DEFAULT_FOLDERS:
        doc = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": template["name"],
            "type": template["type"],
            "is_default": template["is_default"],
            "created_at": now,
            "updated_at": now,
        }
        await db.folders.insert_one(doc)
        docs.append(doc)
    return docs


@router.get("", response_model=List[Folder])
async def get_folders(token: str = Query(...)):
    user = await get_user_by_token(token)
    db = get_db()
    user_id = str(user["_id"])
    docs = await _ensure_default_folders(db, user_id)
    return [_folder_from_doc(doc) for doc in docs]


@router.post("", response_model=Folder)
async def create_folder(data: FolderCreate, token: str = Query(...)):
    user = await get_user_by_token(token)
    db = get_db()
    user_id = str(user["_id"])

    existing = await db.folders.find_one({"user_id": user_id, "name": data.name})
    if existing:
        raise HTTPException(status_code=409, detail="Folder with this name already exists")

    now = datetime.utcnow()
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "name": data.name,
        "type": data.type,
        "is_default": False,
        "created_at": now,
        "updated_at": now,
    }
    await db.folders.insert_one(doc)
    return _folder_from_doc(doc)


@router.put("/{folder_id}", response_model=Folder)
async def update_folder(folder_id: str, data: FolderUpdate, token: str = Query(...)):
    user = await get_user_by_token(token)
    db = get_db()
    user_id = str(user["_id"])

    folder = await db.folders.find_one({"id": folder_id, "user_id": user_id})
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    update = {"updated_at": datetime.utcnow()}
    if data.name is not None:
        existing = await db.folders.find_one(
            {"user_id": user_id, "name": data.name, "id": {"$ne": folder_id}}
        )
        if existing:
            raise HTTPException(status_code=409, detail="Folder with this name already exists")
        update["name"] = data.name

    from pymongo import ReturnDocument
    result = await db.folders.find_one_and_update(
        {"id": folder_id, "user_id": user_id},
        {"$set": update},
        return_document=ReturnDocument.AFTER,
    )
    return _folder_from_doc(result)


@router.delete("/{folder_id}")
async def delete_folder(folder_id: str, token: str = Query(...)):
    user = await get_user_by_token(token)
    db = get_db()
    user_id = str(user["_id"])

    folder = await db.folders.find_one({"id": folder_id, "user_id": user_id})
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    # Prevent deleting the only deadlines-type folder
    if folder.get("type") == "deadlines":
        deadlines_count = await db.folders.count_documents(
            {"user_id": user_id, "type": "deadlines"}
        )
        if deadlines_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete the only deadlines folder"
            )

    # Cascade delete content
    await db.deadlines.delete_many({"user_id": user_id, "folder_id": folder_id})
    await db.notes.delete_many({"user_id": user_id, "folder_id": folder_id})
    await db.folders.delete_one({"id": folder_id, "user_id": user_id})

    return {"deleted": True}
