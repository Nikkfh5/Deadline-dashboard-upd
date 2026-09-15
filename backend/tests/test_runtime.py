"""Regression tests for a disconnected channel reader hidden by a healthy API."""
import os
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.mark.asyncio
@pytest.mark.parametrize("connected", [False, True])
async def test_channel_job_recovers_disconnected_userbot(monkeypatch, connected):
    from scheduler.jobs import channel_check
    from telegram_userbot import client as userbot

    client = Mock()
    client.is_connected.return_value = connected
    client.connect = AsyncMock()
    client.get_me = AsyncMock()
    client.catch_up = AsyncMock()
    monkeypatch.setattr(userbot, "get_userbot", lambda: client)
    join = AsyncMock()
    monkeypatch.setattr(channel_check, "join_pending_channels", join)

    await channel_check.channel_join_job()

    assert client.connect.await_count == (0 if connected else 1)
    assert client.get_me.await_count == (0 if connected else 1)
    assert client.catch_up.await_count == (0 if connected else 1)
    join.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("connected", [False, True])
async def test_health_includes_channel_reader(monkeypatch, connected):
    from server import health_check
    from services import database
    from telegram_bot import bot
    from telegram_userbot import client as userbot

    monkeypatch.setattr(database, "get_db", lambda: SimpleNamespace(command=AsyncMock()))
    monkeypatch.setattr(bot, "get_bot_app", lambda: SimpleNamespace(
        running=True, updater=SimpleNamespace(running=True)))
    monkeypatch.setattr(userbot, "get_userbot", lambda: SimpleNamespace(
        is_connected=lambda: connected))

    result = await health_check()

    assert result["status"] == ("ok" if connected else "degraded")
    assert result["services"]["telegram_userbot"] == ("running" if connected else "disconnected")


@pytest.mark.asyncio
@pytest.mark.parametrize("channel_id,username,path", [
    (123456, "course", "course"), (123456, None, "c/123456"),
    (-630146323, None, "c/3664820973"),
])
async def test_import_carries_original_message_link(monkeypatch, channel_id, username, path):
    from bson import ObjectId
    from telethon.tl.types import Channel
    from telegram_userbot import monitor
    from services import notifications

    user_id = ObjectId()
    chat = Mock(spec=Channel, id=channel_id, username=username, title="Course chat")
    event = SimpleNamespace(get_chat=AsyncMock(return_value=chat),
                            message=SimpleNamespace(id=42, text="An exam next week"))
    sources = [{"_id": ObjectId(), "user_id": str(user_id)}]
    db = SimpleNamespace(
        sources=SimpleNamespace(find=Mock(return_value=SimpleNamespace(to_list=AsyncMock(return_value=sources)))),
        users=SimpleNamespace(find=Mock(return_value=SimpleNamespace(to_list=AsyncMock(return_value=[{"_id": user_id}])))),
        parsed_posts=SimpleNamespace(find_one=AsyncMock(return_value={"extracted_deadlines": [{"subject": "Math"}]})),
    )
    save = AsyncMock(return_value=(0, []))
    send = AsyncMock()
    monkeypatch.setattr(monitor, "get_db", lambda: db)
    monkeypatch.setattr(monitor, "save_extracted_deadlines", save)
    monkeypatch.setattr(notifications, "send_pending_notifications", send)

    await monitor._handle_message(event)

    assert save.call_args.kwargs["source_url"] == f"https://t.me/{path}/42"
    assert save.call_args.kwargs["source_name"] == "Course chat"
    send.assert_awaited_once()


@pytest.mark.asyncio
async def test_notification_retry_job_is_scheduled():
    from scheduler import scheduler
    from services.notifications import send_pending_notifications

    scheduler.setup_scheduler()
    try:
        job = scheduler._scheduler.get_job("notifications")
        assert job.func is send_pending_notifications
        assert job.trigger.interval.total_seconds() == 60
        assert job.max_instances == 1
        assert scheduler._scheduler.get_job("wiki_check") is None
    finally:
        scheduler.shutdown_scheduler()
