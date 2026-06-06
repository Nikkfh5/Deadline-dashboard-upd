"""Tests for deadline router behavior."""
import os
import sys
from datetime import datetime

import pytest
import starlette.routing

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Local test env has a FastAPI/Starlette constructor mismatch. The app runtime
# path is unchanged; this only lets the test import router modules directly.
_router_init = starlette.routing.Router.__init__


def _compatible_router_init(self, *args, **kwargs):
    kwargs.pop("on_startup", None)
    kwargs.pop("on_shutdown", None)
    kwargs.pop("lifespan", None)
    return _router_init(self, *args, **kwargs)


starlette.routing.Router.__init__ = _compatible_router_init

from routers import deadlines as deadlines_router


class _DeleteResult:
    def __init__(self, deleted_count):
        self.deleted_count = deleted_count


class _FakeDeadlines:
    def __init__(self, deleted_count=2):
        self.deleted_count = deleted_count
        self.delete_query = None

    async def delete_many(self, query):
        self.delete_query = query
        return _DeleteResult(self.deleted_count)


class _FakeFolders:
    def __init__(self, folder=None):
        self.folder = folder

    async def find_one(self, query):
        return self.folder


class _FakeDb:
    def __init__(self, folder=None, deleted_count=2):
        self.deadlines = _FakeDeadlines(deleted_count=deleted_count)
        self.folders = _FakeFolders(folder=folder)


@pytest.fixture
def router_auth(monkeypatch):
    async def fake_get_user_by_token(token):
        return {"_id": "user-1"}

    monkeypatch.setattr(deadlines_router, "get_user_by_token", fake_get_user_by_token)


@pytest.mark.asyncio
async def test_delete_expired_deadlines_scopes_to_user(monkeypatch, router_auth):
    fake_db = _FakeDb(deleted_count=3)
    monkeypatch.setattr(deadlines_router, "get_db", lambda: fake_db)

    result = await deadlines_router.delete_expired_deadlines(token="token")

    assert result == {"deleted": 3}
    assert fake_db.deadlines.delete_query["user_id"] == "user-1"
    assert isinstance(fake_db.deadlines.delete_query["due_date"]["$lt"], datetime)


@pytest.mark.asyncio
async def test_delete_expired_deadlines_preserves_default_folder_scope(monkeypatch, router_auth):
    fake_db = _FakeDb(folder={"id": "folder-1", "user_id": "user-1", "is_default": True})
    monkeypatch.setattr(deadlines_router, "get_db", lambda: fake_db)

    await deadlines_router.delete_expired_deadlines(token="token", folder_id="folder-1")

    assert fake_db.deadlines.delete_query["user_id"] == "user-1"
    assert fake_db.deadlines.delete_query["$or"] == [
        {"folder_id": "folder-1"},
        {"folder_id": None},
        {"folder_id": {"$exists": False}},
    ]
    assert isinstance(fake_db.deadlines.delete_query["due_date"]["$lt"], datetime)
