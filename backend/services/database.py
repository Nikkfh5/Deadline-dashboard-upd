from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
import os
import logging

logger = logging.getLogger(__name__)

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


def get_db() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _db


async def init_db() -> AsyncIOMotorDatabase:
    global _client, _db
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "deadline_tracker")
    _client = AsyncIOMotorClient(mongo_url)
    _db = _client[db_name]

    # Create indexes
    await _db.users.create_index("telegram_id", unique=True)
    await _db.users.create_index("dashboard_token", unique=True)
    await _db.sources.create_index([("user_id", 1), ("type", 1), ("identifier", 1)], unique=True)
    await _db.deadlines.create_index([("user_id", 1), ("due_date", 1)])
    await _db.deadlines.create_index("id", unique=True)
    await _db.deadlines.create_index([("user_id", 1), ("name", 1), ("task", 1), ("due_date", 1)])
    await _db.parsed_posts.create_index([("source_id", 1), ("content_hash", 1)], unique=True)

    logger.info(f"Connected to MongoDB: {db_name}")
    return _db


async def close_db():
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
        logger.info("MongoDB connection closed")
