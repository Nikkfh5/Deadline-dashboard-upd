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
