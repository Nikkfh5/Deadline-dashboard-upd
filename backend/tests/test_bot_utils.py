"""Tests for bot handler utility functions."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
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
        assert result == "+abc123"

    def test_whitespace(self):
        assert _normalize_channel("  @test  ") == "@test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
