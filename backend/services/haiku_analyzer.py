import anthropic
import asyncio
import json
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

TELEGRAM_ANALYSIS_PROMPT = """Ты анализируешь пост из Telegram-канала на наличие информации о дедлайнах.
Пост может быть на русском или английском. Ищи домашние задания, контрольные, экзамены и другие учебные дедлайны.

СЕГОДНЯ: {today}

Ключевые слова: ДЗ, домашнее задание, контрольная, КР, экзамен, зачёт, лабораторная, лаба,
дедлайн, deadline, срок сдачи, до, к, assignment, homework, exam, test, quiz, коллоквиум.

Название канала: {channel_name}
{context_block}
Текст поста для анализа:
---
{post_text}
---

Правила:
1. Определи предмет по контексту канала (предыдущие посты, название). Если канал относится к конкретному предмету — используй его. Если канал общий — определи по содержанию поста.
2. ОБЯЗАТЕЛЬНО разреши относительные даты: "завтра" = следующий день от СЕГОДНЯ, "послезавтра" = +2 дня, "в пятницу" = ближайшая пятница, "через неделю" = +7 дней. Никогда не возвращай null для due_date если в тексте есть хоть какое-то указание на срок.
3. Извлеки важные детали: куда сдавать (ссылка, бумажный формат, google classroom), особые условия.

Ответь JSON-объектом:
{{
  "has_deadline": true/false,
  "deadlines": [
    {{
      "task_name": "краткое описание задания (например ДЗ 3)",
      "subject": "название предмета",
      "due_date": "YYYY-MM-DDTHH:MM:SS по московскому времени",
      "confidence": 0.0-1.0,
      "details": "куда сдавать, ссылки, особые условия (кратко)"
    }}
  ],
  "reasoning": "краткое объяснение"
}}

Если дедлайн не найден: {{"has_deadline": false, "deadlines": [], "reasoning": "..."}}.
Извлекай только дедлайны с уверенностью >= 0.6.
Если год не указан, считай текущий учебный год ({current_year}).
Если время не указано, по умолчанию 23:59.
Отвечай ТОЛЬКО валидным JSON без markdown-обёрток."""

WIKI_ANALYSIS_PROMPT = """Ты извлекаешь информацию о дедлайнах с академической вики-страницы.
Страница может содержать таблицы с заданиями и их сроками.

HTML-содержимое страницы:
---
{page_content}
---

URL страницы: {url}

Извлеки все дедлайны. Ответь JSON:
{{
  "deadlines": [
    {{
      "task_name": "например ДЗ 1",
      "subject": "название курса из заголовка страницы или контекста",
      "due_date": "YYYY-MM-DDTHH:MM:SS",
      "confidence": 0.0-1.0
    }}
  ]
}}

Для дат вроде "14.09, 23:59" используй текущий учебный год ({current_year}).
Конвертируй все даты в ISO8601 формат.
Отвечай ТОЛЬКО валидным JSON без markdown-обёрток."""

DATE_PARSE_PROMPT = """Пользователь вводит дату/время дедлайна в свободной форме. Разбери текст и верни точную дату.

СЕГОДНЯ: {today}

Текст пользователя: "{user_text}"

Правила:
- "завтра" = следующий день, "послезавтра" = +2 дня
- "в пятницу", "в среду" = ближайший такой день недели (если сегодня этот день — берём следующую неделю)
- "через N дней/недель" = +N дней/недель от сегодня
- Если время не указано — 23:59
- Все даты в московском часовом поясе
- Если год не указан — текущий; если дата уже прошла в этом году — следующий год

Ответь ТОЛЬКО JSON без markdown:
{{"date": "YYYY-MM-DDTHH:MM:SS", "parsed": true}}

Если не удалось распознать:
{{"date": null, "parsed": false}}"""


MAX_API_RETRIES = 3


class HaikuAnalyzer:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if self.api_key:
            self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
        else:
            self.client = None
            logger.warning("ANTHROPIC_API_KEY not set, HaikuAnalyzer disabled")

    async def _api_call(self, **kwargs) -> str:
        """Call Anthropic API with retry and backoff."""
        last_error = None
        for attempt in range(MAX_API_RETRIES):
            try:
                response = await self.client.messages.create(**kwargs)
                return response.content[0].text.strip()
            except anthropic.APIError as e:
                last_error = e
                if attempt < MAX_API_RETRIES - 1:
                    await asyncio.sleep(2 ** attempt)
                    logger.warning(f"Haiku API retry {attempt + 1}/{MAX_API_RETRIES}: {e}")
        raise last_error

    async def analyze_post(self, text: str, channel_name: str = "", channel_context: str = "") -> dict:
        if not self.client:
            return {"has_deadline": False, "deadlines": [], "reasoning": "API key not configured"}

        current_year = _get_academic_year()

        context_block = ""
        if channel_context:
            # Trim context to avoid huge prompts
            trimmed = channel_context[:3000]
            context_block = f"\nПредыдущие посты канала (для определения предмета/тематики):\n---\n{trimmed}\n---\n"

        today = datetime.now().strftime("%Y-%m-%d (%A)")

        prompt = TELEGRAM_ANALYSIS_PROMPT.format(
            post_text=text,
            channel_name=channel_name,
            current_year=current_year,
            context_block=context_block,
            today=today,
        )

        try:
            raw = await self._api_call(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            return _extract_json(raw)
        except (anthropic.APIError, json.JSONDecodeError, ValueError) as e:
            logger.error(f"Haiku analyze_post error: {e}")
            return {"has_deadline": False, "deadlines": [], "reasoning": str(e)}

    async def parse_date(self, user_text: str) -> Optional[datetime]:
        """Parse natural language date using Haiku. Returns datetime in UTC or None."""
        if not self.client:
            return None

        today = datetime.now().strftime("%Y-%m-%d (%A)")
        prompt = DATE_PARSE_PROMPT.format(today=today, user_text=user_text)

        try:
            raw = await self._api_call(
                model="claude-haiku-4-5-20251001",
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}],
            )
            data = _extract_json(raw)
            if data.get("parsed") and data.get("date"):
                dt = datetime.fromisoformat(data["date"])
                return dt - timedelta(hours=3)
        except (anthropic.APIError, json.JSONDecodeError, ValueError) as e:
            logger.error(f"Haiku date parse error: {e}")
        return None

    async def analyze_wiki(self, html_content: str, url: str) -> list:
        if not self.client:
            return []

        # Truncate to avoid token limits
        content = html_content[:15000]
        current_year = _get_academic_year()
        prompt = WIKI_ANALYSIS_PROMPT.format(
            page_content=content,
            url=url,
            current_year=current_year,
        )

        try:
            raw = await self._api_call(
                model="claude-haiku-4-5-20251001",
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
            data = _extract_json(raw)
            return data.get("deadlines", [])
        except (anthropic.APIError, json.JSONDecodeError, ValueError) as e:
            logger.error(f"Haiku wiki analysis error: {e}")
            return []


def _extract_json(raw: str) -> dict:
    """Extract JSON from raw response, stripping markdown code fences if present."""
    text = raw.strip()
    # Remove ```json ... ``` or ``` ... ```
    match = re.search(r'```(?:json)?\s*\n?(.*?)```', text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    return json.loads(text)


def _get_academic_year() -> str:
    now = datetime.now()
    if now.month >= 9:
        return f"{now.year}/{now.year + 1}"
    return f"{now.year - 1}/{now.year}"


_instance: Optional[HaikuAnalyzer] = None


def get_analyzer() -> HaikuAnalyzer:
    global _instance
    if _instance is None:
        _instance = HaikuAnalyzer()
    return _instance
