"""Tests for bot handler utility functions."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from telegram_bot.handlers.channels import _normalize_channel


class TestNormalizeChannel:
    def test_plain_username(self):
        assert _normalize_channel("test_channel") == "@test_channel"

    def test_with_at(self):
        assert _normalize_channel("@test_channel") == "@test_channel"

    def test_tme_link(self):
        assert _normalize_channel("https://t.me/test_channel") == "@test_channel"

    def test_tme_link_http(self):
        assert _normalize_channel("http://t.me/test_channel") == "@test_channel"

    def test_invite_link(self):
        result = _normalize_channel("+abc123")
        assert result == "invite:abc123"

    def test_whitespace(self):
        assert _normalize_channel("  @test  ") == "@test"


@pytest.mark.asyncio
async def test_completion_cannot_delete_another_users_deadline(monkeypatch):
    from telegram_bot.handlers import deadlines

    foreign = {"id": "foreign", "user_id": "owner", "name": "Task"}
    db = SimpleNamespace(deadlines=SimpleNamespace(
        find_one=AsyncMock(side_effect=lambda query: foreign if all(
            foreign.get(k) == v for k, v in query.items()) else None),
        delete_one=AsyncMock()), completions=SimpleNamespace(insert_one=AsyncMock()))
    monkeypatch.setattr(deadlines, "get_db", lambda: db)
    monkeypatch.setattr(deadlines, "get_current_user", AsyncMock(return_value={"_id": "other"}))
    monkeypatch.setattr(deadlines, "my_deadlines_command", AsyncMock())
    update = SimpleNamespace(callback_query=SimpleNamespace(
        data="done_dl:foreign", answer=AsyncMock()))

    await deadlines.complete_deadline_button(update, None)

    db.deadlines.delete_one.assert_not_awaited()
    db.completions.insert_one.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["channels", "wiki"])
async def test_source_conversation_cancel_is_async_and_clears_state(kind):
    from telegram_bot.handlers import channels, wiki

    module = channels if kind == "channels" else wiki
    handler = (module.build_add_channel_conversation() if kind == "channels"
               else module.build_add_wiki_conversation())
    cancel = next(h.callback for h in handler.fallbacks if getattr(h, "commands", None))
    key = "add_channel_user" if kind == "channels" else "add_wiki_user"
    context = SimpleNamespace(user_data={key: {"_id": "user"}})
    update = SimpleNamespace(callback_query=None, message=SimpleNamespace(reply_text=AsyncMock()))

    await cancel(update, context)

    assert key not in context.user_data
    update.message.reply_text.assert_awaited_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
