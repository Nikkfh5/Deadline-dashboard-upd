from fastapi import APIRouter, HTTPException, Query, Request
from typing import List
from datetime import datetime
from bson import ObjectId

from models.source import Source, SourceCreate
from services.database import get_db
from services.auth import get_user_by_token
from services import manytask

router = APIRouter(prefix="/api/sources", tags=["sources"])


def _source_from_doc(doc: dict) -> Source:
    return Source(
        id=str(doc["_id"]),
        user_id=str(doc["user_id"]),
        type=doc["type"],
        identifier=doc["identifier"],
        display_name=doc["display_name"],
        is_active=doc.get("is_active", True),
        joined=doc.get("joined", False),
        last_checked_at=doc.get("last_checked_at"),
        last_post_id=doc.get("last_post_id"),
        last_content_hash=doc.get("last_content_hash"),
        last_error=doc.get("last_error"),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


@router.get("", response_model=List[Source])
async def get_sources(token: str = Query(...)):
    user = await get_user_by_token(token)
    db = get_db()
    user_id = str(user["_id"])
    docs = await db.sources.find({"user_id": user_id, "is_active": True}).to_list(100)
    return [_source_from_doc(doc) for doc in docs]


@router.post("", response_model=Source)
async def create_source(data: SourceCreate, token: str = Query(...)):
    user = await get_user_by_token(token)
    if data.type == "manytask_course":
        raise HTTPException(status_code=400, detail="Подключите Manytask через форму входа.")
    db = get_db()
    user_id = str(user["_id"])

    existing = await db.sources.find_one({
        "user_id": user_id,
        "type": data.type,
        "identifier": data.identifier,
    })
    if existing:
        if not existing.get("is_active", True):
            await db.sources.update_one(
                {"_id": existing["_id"]},
                {"$set": {"is_active": True, "updated_at": datetime.utcnow()}},
            )
            existing["is_active"] = True
        return _source_from_doc(existing)

    now = datetime.utcnow()
    doc = {
        "user_id": user_id,
        "type": data.type,
        "identifier": data.identifier,
        "display_name": data.display_name or data.identifier,
        "is_active": True,
        "joined": False,
        "last_checked_at": None,
        "last_post_id": None,
        "last_content_hash": None,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.sources.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _source_from_doc(doc)


@router.get("/manytask")
async def manytask_status(token: str = Query(...)):
    user = await get_user_by_token(token)
    try:
        manytask.session_cipher()
        configured = True
    except manytask.ManytaskError:
        configured = False
    docs = await get_db().sources.find({
        "user_id": str(user["_id"]), "type": "manytask_course", "is_active": True,
    }).to_list(None)
    return {"configured": configured, "connected": configured and bool(user.get("manytask_session")),
            "sources": [_source_from_doc(doc) for doc in docs]}


@router.post("/manytask", response_model=Source)
async def connect_manytask(request: Request, token: str = Query(...)):
    user = await get_user_by_token(token)
    # Validate explicitly: standard 422 validation details can echo password input.
    try:
        data = await request.json()
    except ValueError:
        raise HTTPException(status_code=400, detail="Некорректные данные подключения.") from None
    if not isinstance(data, dict) or any(not isinstance(data.get(k, ""), str) for k in ("identifier", "username", "password")):
        raise HTTPException(status_code=400, detail="Укажите ссылку курса, логин и пароль текстом.")
    url, username, password = (data.get(k, "") for k in ("identifier", "username", "password"))
    username = username.strip()
    if len(url) > 250 or len(username) > 254 or len(password) > 1024 or bool(username) != bool(password):
        raise HTTPException(status_code=400, detail="Проверьте ссылку курса, логин и пароль.")
    try:
        source = await manytask.connect_course(user["_id"], url, username, password)
    except manytask.ManytaskError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None
    return _source_from_doc(source)


@router.delete("/{source_id}")
async def delete_source(source_id: str, token: str = Query(...)):
    user = await get_user_by_token(token)
    db = get_db()
    user_id = str(user["_id"])
    if not ObjectId.is_valid(source_id):
        raise HTTPException(status_code=404, detail="Source not found")
    async with manytask.account_lock(user_id):
        result = await db.sources.update_one(
            {"_id": ObjectId(source_id), "user_id": user_id},
            {"$set": {"is_active": False, "updated_at": datetime.utcnow()}},
        )
        if not await db.sources.find_one({"user_id": user_id, "type": "manytask_course", "is_active": True}):
            await db.users.update_one({"_id": user["_id"]}, {"$unset": {"manytask_session": ""}})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Source not found")
    return {"deactivated": True}
