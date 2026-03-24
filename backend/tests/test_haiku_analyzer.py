"""Tests for Haiku analyzer prompt formatting and response parsing."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from services.haiku_analyzer import _get_academic_year, TELEGRAM_ANALYSIS_PROMPT, WIKI_ANALYSIS_PROMPT


class TestAcademicYear:
    def test_returns_string(self):
        result = _get_academic_year()
        assert isinstance(result, str)
        assert "/" in result

    def test_format(self):
        result = _get_academic_year()
        parts = result.split("/")
        assert len(parts) == 2
        assert int(parts[0]) > 2020
        assert int(parts[1]) > 2020


class TestPromptTemplates:
    def test_telegram_prompt_has_placeholders(self):
        assert "{post_text}" in TELEGRAM_ANALYSIS_PROMPT
        assert "{channel_name}" in TELEGRAM_ANALYSIS_PROMPT
        assert "{current_year}" in TELEGRAM_ANALYSIS_PROMPT

    def test_telegram_prompt_formats(self):
        result = TELEGRAM_ANALYSIS_PROMPT.format(
            post_text="ДЗ 3 до 28.09",
            channel_name="@test_channel",
            current_year="2025/2026",
        )
        assert "ДЗ 3 до 28.09" in result
        assert "@test_channel" in result

    def test_wiki_prompt_has_placeholders(self):
        assert "{page_content}" in WIKI_ANALYSIS_PROMPT
        assert "{url}" in WIKI_ANALYSIS_PROMPT
        assert "{current_year}" in WIKI_ANALYSIS_PROMPT

    def test_wiki_prompt_formats(self):
        result = WIKI_ANALYSIS_PROMPT.format(
            page_content="<table>...</table>",
            url="http://wiki.cs.hse.ru/Test",
            current_year="2025/2026",
        )
        assert "<table>...</table>" in result


class TestHaikuAnalyzerNoKey:
    def test_no_key_returns_empty(self):
        from services.haiku_analyzer import HaikuAnalyzer
        analyzer = HaikuAnalyzer(api_key="")
        assert analyzer.client is None

    @pytest.mark.asyncio
    async def test_analyze_post_no_key(self):
        from services.haiku_analyzer import HaikuAnalyzer
        analyzer = HaikuAnalyzer(api_key="")
        result = await analyzer.analyze_post("test text")
        assert result["has_deadline"] is False

    @pytest.mark.asyncio
    async def test_analyze_wiki_no_key(self):
        from services.haiku_analyzer import HaikuAnalyzer
        analyzer = HaikuAnalyzer(api_key="")
        result = await analyzer.analyze_wiki("<html>test</html>", "http://test.com")
        assert result == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
