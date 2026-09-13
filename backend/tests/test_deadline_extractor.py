"""Channel analysis dates must follow the same UTC storage contract as manual input."""
import os
import sys
from datetime import datetime
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
