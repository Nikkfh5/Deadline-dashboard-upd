"""Tests for Pydantic models."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime
from models.deadline import Deadline, DeadlineCreate, DeadlineUpdate, DeadlineSource
from models.user import User, UserCreate, UserSettings
from models.source import Source, SourceCreate
from models.parsed_post import ParsedPost, ExtractedDeadline


class TestDeadlineModels:
    def test_deadline_create(self):
        d = DeadlineCreate(
            name="Матан",
            task="ДЗ 1",
            due_date=datetime(2025, 9, 14, 23, 59),
        )
        assert d.name == "Матан"
        assert d.is_recurring is False
        assert d.source.type == "manual"

    def test_deadline_create_with_source(self):
        d = DeadlineCreate(
            name="Матан",
            task="ДЗ 1",
            due_date=datetime(2025, 9, 14, 23, 59),
            source=DeadlineSource(type="telegram", source_id="123"),
        )
        assert d.source.type == "telegram"

    def test_deadline_update_partial(self):
        d = DeadlineUpdate(name="Updated name")
        dumped = d.model_dump(exclude_unset=True)
        assert "name" in dumped
        assert "task" not in dumped

    def test_deadline_full(self):
        d = Deadline(
            id="123",
            name="Матан",
            task="ДЗ 1",
            due_date=datetime(2025, 9, 14, 23, 59),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        assert d.id == "123"
        assert d.is_postponed is False


class TestUserModels:
    def test_user_create(self):
        u = UserCreate(
            telegram_id=12345,
            first_name="Test",
        )
        assert u.telegram_id == 12345
        assert u.telegram_username is None

    def test_user_settings_defaults(self):
        s = UserSettings()
        assert s.check_interval_minutes == 60
        assert s.timezone == "Europe/Moscow"
        assert s.notifications_enabled is True

    def test_user_full(self):
        u = User(
            id="abc",
            telegram_id=12345,
            first_name="Test",
            dashboard_token="uuid-here",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        assert u.settings.timezone == "Europe/Moscow"


class TestSourceModels:
    def test_source_create_channel(self):
        s = SourceCreate(
            type="telegram_channel",
            identifier="@test_channel",
        )
        assert s.type == "telegram_channel"
        assert s.display_name is None

    def test_source_create_wiki(self):
        s = SourceCreate(
            type="wiki_page",
            identifier="http://wiki.cs.hse.ru/Test",
            display_name="Test page",
        )
        assert s.display_name == "Test page"


class TestParsedPostModels:
    def test_extracted_deadline(self):
        e = ExtractedDeadline(
            task_name="ДЗ 1",
            subject="Матан",
            due_date="2025-09-14T23:59:00",
            confidence=0.95,
        )
        assert e.confidence == 0.95

    def test_parsed_post(self):
        p = ParsedPost(
            id="abc",
            source_id="src1",
            content_hash="hash123",
            raw_text="Some text",
            has_deadline=True,
            extracted_deadlines=[],
            processed_at=datetime.utcnow(),
        )
        assert p.has_deadline is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
