"""Delivery contracts; MongoDB and Telegram are the only mocked boundaries."""
import asyncio
import os
import sys
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from bson import ObjectId
from telegram.error import BadRequest, Forbidden, NetworkError, RetryAfter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def delivery(monkeypatch):
    from services import notifications
    from telegram_bot import bot

    user = {"_id": ObjectId(), "telegram_id": 123, "dashboard_token": "test-token"}
    doc = {
        "id": "deadline", "user_id": str(user["_id"]), "name": "Матстат",
        "task": "ДЗ №3 | Решить задачи 1–5, загрузить PDF в LMS.",
        "due_date": datetime(2026, 9, 19, 20, 59),
        "notifications": [{
            "id": "event", "source_name": "Матстат — объявления",
            "source_url": "https://t.me/course/42", "next_attempt_at": datetime(2026, 1, 1),
            "name": "Матстат", "task": "ДЗ №3 | Решить задачи 1–5, загрузить PDF в LMS.",
            "due_date": datetime(2026, 9, 19, 20, 59),
        }],
    }
    docs = [doc]
    db = SimpleNamespace(
        users=SimpleNamespace(find_one=AsyncMock(return_value=user)),
        deadlines=SimpleNamespace(
            find_one=AsyncMock(side_effect=[doc, None]),
            find=Mock(return_value=SimpleNamespace(to_list=AsyncMock(return_value=docs))),
            update_many=AsyncMock()),
    )
    send = AsyncMock()
    monkeypatch.setattr(notifications, "get_db", lambda: db)
    monkeypatch.setattr(bot, "get_bot_app", lambda: SimpleNamespace(bot=SimpleNamespace(send_message=send)))
    monkeypatch.setenv("FRONTEND_URL", "https://dashboard.example")
    return SimpleNamespace(service=notifications, db=db, doc=doc, docs=docs, user=user, send=send)


@pytest.mark.asyncio
async def test_sends_saved_summary_moscow_time_and_links(delivery):
    await delivery.service.send_pending_notifications()

    message = delivery.send.call_args.kwargs
    assert message["chat_id"] == 123
    for expected in ("Добавлен новый дедлайн", "Матстат", "ДЗ №3",
                     "Решить задачи 1–5", "19.09.2026 23:59 МСК", "Матстат — объявления"):
        assert expected in message["text"]
    buttons = message["reply_markup"].inline_keyboard[0]
    assert [button.url for button in buttons] == [
        "https://t.me/course/42", "https://dashboard.example?token=test-token"]
    assert delivery.db.deadlines.find.call_args.args[0] == {
        "user_id": delivery.doc["user_id"], "notifications.id": "event"}
    assert delivery.db.deadlines.update_many.call_args.args == (
        {"user_id": delivery.doc["user_id"], "notifications.id": "event"},
        {"$pull": {"notifications": {"id": "event"}}},
    )


@pytest.mark.asyncio
async def test_one_message_for_multiple_tasks_and_long_text(delivery):
    for i in range(20):
        doc = deepcopy(delivery.doc)
        doc.update(id=str(i), name="Предмет" * 80, task="Задание 📝" * 80)
        doc["notifications"][0].update(name=doc["name"], task=doc["task"])
        delivery.docs.append(doc)
    await delivery.service.send_pending_notifications()

    delivery.send.assert_awaited_once()
    text = delivery.send.call_args.kwargs["text"]
    assert "(21)" in text
    assert "ещё" in text
    assert len(text.encode("utf-16-le")) // 2 <= 4096


@pytest.mark.asyncio
async def test_reschedule_shows_old_and_new_moscow_dates(delivery):
    delivery.doc["notifications"][0]["old_date"] = datetime(2026, 9, 18, 20, 59, tzinfo=timezone.utc)
    await delivery.service.send_pending_notifications()

    text = delivery.send.call_args.kwargs["text"]
    assert "Перенос" in text
    assert "18.09.2026 23:59 МСК" in text and "19.09.2026 23:59 МСК" in text
    assert "Добавлен" not in text


@pytest.mark.asyncio
@pytest.mark.parametrize("error,delay", [
    (NetworkError("offline"), 60), (RetryAfter(125), 125), (RetryAfter(timedelta(seconds=130)), 130),
])
async def test_transient_error_retains_notification_until_retry(delivery, error, delay):
    delivery.send.side_effect = error
    before = datetime.now(timezone.utc).replace(tzinfo=None)
    await delivery.service.send_pending_notifications()

    query, update = delivery.db.deadlines.update_many.call_args.args
    assert query["notifications.id"] == "event"
    due = update["$set"]["notifications.$[event].next_attempt_at"]
    assert before + timedelta(seconds=delay) <= due <= datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=delay)
    assert "$pull" not in update
    assert delivery.db.deadlines.update_many.call_args.kwargs["array_filters"] == [{"event.id": "event"}]


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [Forbidden("blocked"), BadRequest("chat not found")])
async def test_permanent_delivery_error_does_not_retry_forever(delivery, error):
    delivery.send.side_effect = error
    await delivery.service.send_pending_notifications()

    assert delivery.db.deadlines.update_many.call_args.args[1] == {"$pull": {"notifications": {"id": "event"}}}


@pytest.mark.asyncio
@pytest.mark.parametrize("user", [None, {"settings": {"notifications_enabled": False}}])
async def test_missing_or_disabled_user_does_not_receive_backlog(delivery, user):
    delivery.db.users.find_one.return_value = user
    await delivery.service.send_pending_notifications()

    delivery.send.assert_not_awaited()
    assert delivery.db.deadlines.update_many.call_args.args[1] == {"$pull": {"notifications": {"id": "event"}}}


@pytest.mark.asyncio
async def test_pending_message_uses_original_snapshot_after_later_reschedule(delivery):
    delivery.doc["due_date"] = datetime(2026, 9, 30)
    delivery.doc["task"] = "A later revision"
    delivery.doc["notifications"].append({
        **delivery.doc["notifications"][0], "id": "later-event",
        "next_attempt_at": datetime(2099, 1, 1),
        "old_date": datetime(2026, 9, 19, 20, 59), "due_date": datetime(2026, 9, 30),
    })
    await delivery.service.send_pending_notifications()

    text = delivery.send.call_args.kwargs["text"]
    assert "19.09.2026 23:59 МСК" in text
    assert "ДЗ №3" in text and "A later revision" not in text
    assert delivery.db.deadlines.update_many.call_args.args[1] == {"$pull": {"notifications": {"id": "event"}}}


@pytest.mark.asyncio
async def test_bot_unavailable_leaves_pending_records(delivery, monkeypatch):
    from telegram_bot import bot
    monkeypatch.setattr(bot, "get_bot_app", lambda: None)
    await delivery.service.send_pending_notifications()

    delivery.send.assert_not_awaited()
    delivery.db.deadlines.update_many.assert_not_awaited()


@pytest.mark.asyncio
async def test_import_can_save_while_telegram_send_is_waiting(delivery, monkeypatch):
    from services import deadline_extractor

    started, release = asyncio.Event(), asyncio.Event()
    async def slow_send(**kwargs):
        started.set()
        await release.wait()
    delivery.send.side_effect = slow_send
    delivery.db.parsed_posts = SimpleNamespace(find_one=AsyncMock(return_value=None), insert_one=AsyncMock())
    delivery.db.deadlines.insert_many = AsyncMock()
    monkeypatch.setattr(deadline_extractor, "get_db", lambda: delivery.db)
    sender = asyncio.create_task(delivery.service.send_pending_notifications())
    await asyncio.wait_for(started.wait(), 1)
    try:
        count, _ = await asyncio.wait_for(deadline_extractor.save_extracted_deadlines(
            [delivery.doc["user_id"]],
            [{"subject": "Biology", "task_name": "Exam", "due_date": "2026-09-20T23:59:00", "confidence": 0.95}],
            "source", "telegram", "Biology exam"), 0.5)
        assert count == 1
    finally:
        release.set()
        await sender
