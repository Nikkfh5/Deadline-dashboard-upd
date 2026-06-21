"""Tests for Haiku analyzer prompt formatting and response parsing."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from services.haiku_analyzer import _get_academic_year, TELEGRAM_ANALYSIS_PROMPT, WIKI_ANALYSIS_PROMPT


class FakeProvider:
    def __init__(self, name, responses, configured=True):
        self.name = name
        self.responses = list(responses)
        self.configured = configured
        self.calls = []

    async def complete(self, prompt: str, max_tokens: int) -> str:
        self.calls.append({"prompt": prompt, "max_tokens": max_tokens})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


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
            today="2026-06-03",
            weekday="Wednesday",
            description_block="",
            subjects_block="",
            context_block="",
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


class TestProviderFallback:
    def test_default_provider_ranking(self, monkeypatch):
        from services.haiku_analyzer import HaikuAnalyzer

        monkeypatch.delenv("LLM_PROVIDER_ORDER", raising=False)
        monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
        monkeypatch.setenv("GROQ_API_KEY", "groq-key")
        monkeypatch.setenv("CEREBRAS_API_KEY", "cerebras-key")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-key")

        analyzer = HaikuAnalyzer()

        assert [provider.name for provider in analyzer.providers] == [
            "gemini",
            "groq",
            "cerebras",
            "haiku",
        ]

    @pytest.mark.asyncio
    async def test_analyze_post_falls_back_after_invalid_json(self):
        from services.haiku_analyzer import HaikuAnalyzer

        gemini = FakeProvider("gemini", ["not json"])
        groq = FakeProvider(
            "groq",
            ['{"analysis": "ok", "has_deadline": true, "deadlines": []}'],
        )
        haiku = FakeProvider(
            "haiku",
            ['{"analysis": "should not run", "has_deadline": false, "deadlines": []}'],
        )
        analyzer = HaikuAnalyzer(providers=[gemini, groq, haiku])

        result = await analyzer.analyze_post("ДЗ до завтра")

        assert result["has_deadline"] is True
        assert len(gemini.calls) == 1
        assert len(groq.calls) == 1
        assert haiku.calls == []

    @pytest.mark.asyncio
    async def test_parse_date_skips_unconfigured_provider(self):
        from services.haiku_analyzer import HaikuAnalyzer

        gemini = FakeProvider("gemini", ['{"parsed": false, "date": null}'], configured=False)
        groq = FakeProvider("groq", ['{"parsed": true, "date": "2026-06-22T23:59:00"}'])
        analyzer = HaikuAnalyzer(providers=[gemini, groq])

        result = await analyzer.parse_date("завтра")

        assert result is not None
        assert result.year == 2026
        assert result.month == 6
        assert result.day == 22
        assert gemini.calls == []
        assert len(groq.calls) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
