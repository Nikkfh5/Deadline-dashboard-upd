"""Channel analysis dates must follow the same UTC storage contract as manual input."""
import os
import sys
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.mark.asyncio
@pytest.mark.parametrize("due", ["2026-09-16T10:30:00", "2026-09-16T10:30:00+03:00", "2026-09-16T07:30:00Z"])
async def test_extracted_deadline_is_stored_in_utc(monkeypatch, due):
    from services import deadline_extractor

    db = SimpleNamespace(
        parsed_posts=SimpleNamespace(find_one=AsyncMock(return_value=None), insert_one=AsyncMock()),
        deadlines=SimpleNamespace(find=Mock(return_value=SimpleNamespace(to_list=AsyncMock(return_value=[]))),
                                  insert_many=AsyncMock()))
    monkeypatch.setattr(deadline_extractor, "get_db", lambda: db)

    count, moved = await deadline_extractor.save_extracted_deadlines(
        ["user"], [{"subject": "Course", "task_name": "Exam", "due_date": due, "confidence": 0.95}],
        "source", "telegram", "Exam at 10:30 Moscow time on 16 September 2026")

    assert count == 1 and moved == []
    assert db.deadlines.insert_many.call_args.args[0][0]["due_date"] == datetime(2026, 9, 16, 7, 30)


@pytest.mark.asyncio
async def test_notifications_only_cover_saved_changes_per_user(monkeypatch):
    from services import deadline_extractor

    existing = [
        {"_id": "existing-a", "user_id": "a", "name": "Math", "task": "Exam",
         "due_date": datetime(2026, 9, 16, 7, 30)},
        {"_id": "existing-b", "user_id": "b", "name": "Math", "task": "Exam",
         "due_date": datetime(2026, 9, 15, 7, 30)},
    ]
    db = SimpleNamespace(
        parsed_posts=SimpleNamespace(find_one=AsyncMock(return_value=None), insert_one=AsyncMock()),
        deadlines=SimpleNamespace(
            find=Mock(return_value=SimpleNamespace(to_list=AsyncMock(return_value=existing))),
            insert_many=AsyncMock(), update_one=AsyncMock()))
    monkeypatch.setattr(deadline_extractor, "get_db", lambda: db)
    extracted = [
        {"subject": "Math", "task_name": "Exam", "due_date": "2026-09-16T10:30:00", "confidence": 0.95},
        {"subject": "History", "task_name": "Essay", "details": "Upload PDF",
         "due_date": "2026-09-18T23:59:00", "confidence": 0.95},
        {"subject": "Rejected", "task_name": "Guess", "due_date": "2026-09-18T23:59:00", "confidence": 0.1},
    ]
    count, moved = await deadline_extractor.save_extracted_deadlines(
        ["a", "b"], extracted, "source", "telegram", "Exam and essay",
        source_name="Course chat", source_url="https://t.me/course/42")

    assert count == 2 and len(moved) == 1
    inserted = db.deadlines.insert_many.call_args.args[0]
    assert [(d["user_id"], d["name"], d["task"]) for d in inserted] == [
        ("a", "History", "Essay | Upload PDF"), ("b", "History", "Essay | Upload PDF")]
    assert inserted[0]["notifications"][0]["id"] != inserted[1]["notifications"][0]["id"]
    for doc in inserted:
        assert doc["notifications"][0]["source_name"] == "Course chat"
        assert doc["notifications"][0]["source_url"] == "https://t.me/course/42"
        assert "old_date" not in doc["notifications"][0]
    query, update = db.deadlines.update_one.call_args.args
    assert query == {"_id": "existing-b", "updated_at": None}
    assert "notifications" not in update["$set"]
    notification = update["$push"]["notifications"]
    assert notification["old_date"] == datetime(2026, 9, 15, 7, 30)
    assert notification["id"] not in {d["notifications"][0]["id"] for d in inserted}
    assert notification["due_date"] == datetime(2026, 9, 16, 7, 30)


@pytest.mark.asyncio
@pytest.mark.parametrize("old_task,new_task,details,post_day,last_seen,expected_new,expected_moved", [
    ("ДЗ 1", "ДЗ 2", "", 20, 19, 1, 0),
    ("HW 1.2", "HW 12", "", 20, 19, 1, 0),
    ("Exam groups 1,2,5,7", "Exam groups 12,5,7", "", 20, 19, 1, 0),
    ("ДЗ №1 | Очень длинные старые условия и ссылка на старую форму", "ДЗ №1", "Новая ссылка", 20, 19, 0, 1),
    ("ДЗ №1", "ДЗ №1", "", 19, 20, 0, 0),
])
async def test_reschedule_identity_and_source_order(
        monkeypatch, old_task, new_task, details, post_day, last_seen, expected_new, expected_moved):
    from services import deadline_extractor
    existing = {"_id": "old", "user_id": "user", "name": "Math", "task": old_task,
                "due_date": datetime(2026, 9, 25), "source_updated_at": datetime(2026, 9, last_seen)}
    db = SimpleNamespace(
        parsed_posts=SimpleNamespace(find_one=AsyncMock(return_value=None), insert_one=AsyncMock()),
        deadlines=SimpleNamespace(
            find=Mock(return_value=SimpleNamespace(to_list=AsyncMock(return_value=[existing]))),
            insert_many=AsyncMock(), update_one=AsyncMock()))
    monkeypatch.setattr(deadline_extractor, "get_db", lambda: db)
    count, moved = await deadline_extractor.save_extracted_deadlines(
        ["user"], [{"subject": "Math", "task_name": new_task, "details": details,
                    "due_date": "2026-09-27T23:59:00", "confidence": .95}],
        "source", "telegram", "New post", post_date=datetime(2026, 9, post_day, tzinfo=timezone.utc))
    assert (count, len(moved)) == (expected_new, expected_moved)
    if expected_moved:
        changes = db.deadlines.update_one.call_args.args[1]["$set"]
        assert changes["source"]["original_text"] == "New post"
        assert changes["source_updated_at"] == datetime(2026, 9, post_day)
    else:
        db.deadlines.update_one.assert_not_awaited()


@pytest.mark.asyncio
async def test_replaying_cached_old_post_does_not_roll_date_back(monkeypatch):
    from services import deadline_extractor
    extracted = [{"subject": "Math", "task_name": "Exam", "due_date": "2026-09-20T23:59:00", "confidence": .95}]
    existing = {"_id": "old", "user_id": "user", "name": "Math", "task": "Exam",
                "due_date": datetime(2026, 9, 27, 20, 59), "source_updated_at": datetime(2026, 9, 19)}
    db = SimpleNamespace(
        parsed_posts=SimpleNamespace(find_one=AsyncMock(return_value={
            "extracted_deadlines": extracted, "processed_at": datetime(2026, 9, 18)})),
        deadlines=SimpleNamespace(
            find=Mock(return_value=SimpleNamespace(to_list=AsyncMock(return_value=[existing]))),
            insert_many=AsyncMock(), update_one=AsyncMock()))
    monkeypatch.setattr(deadline_extractor, "get_db", lambda: db)
    assert await deadline_extractor.save_extracted_deadlines(
        ["user"], extracted, "source", "telegram", "Original exam post") == (0, [])
    db.deadlines.update_one.assert_not_awaited()


def test_cache_separates_same_relative_text_from_different_posts():
    from services.deadline_extractor import content_hash
    assert content_hash("ДЗ до завтра", datetime(2026, 9, 15)) != content_hash("ДЗ до завтра", datetime(2026, 9, 16))


@pytest.mark.asyncio
async def test_import_does_not_overwrite_concurrent_manual_edit(monkeypatch):
    from services import deadline_extractor
    existing = {"_id": "old", "user_id": "user", "name": "Math", "task": "Exam",
                "due_date": datetime(2026, 9, 20), "updated_at": datetime(2026, 9, 15)}
    db = SimpleNamespace(
        parsed_posts=SimpleNamespace(find_one=AsyncMock(return_value=None), insert_one=AsyncMock()),
        deadlines=SimpleNamespace(
            find=Mock(return_value=SimpleNamespace(to_list=AsyncMock(return_value=[existing]))),
            insert_many=AsyncMock(), update_one=AsyncMock(return_value=SimpleNamespace(matched_count=0))))
    monkeypatch.setattr(deadline_extractor, "get_db", lambda: db)
    result = await deadline_extractor.save_extracted_deadlines(
        ["user"], [{"subject": "Math", "task_name": "Exam", "due_date": "2026-09-27T23:59:00", "confidence": .95}],
        "source", "telegram", "Post", post_date=datetime(2026, 9, 16))
    assert result == (0, [])
    assert db.deadlines.update_one.call_args.args[0] == {"_id": "old", "updated_at": datetime(2026, 9, 15)}
