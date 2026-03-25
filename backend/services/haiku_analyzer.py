import anthropic
import json
import logging
import os
import re
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

TELEGRAM_ANALYSIS_PROMPT = """Ты анализируешь пост из Telegram-канала на наличие информации о дедлайнах.
Пост может быть на русском или английском. Ищи домашние задания, контрольные, экзамены и другие учебные дедлайны.

Ключевые слова: ДЗ, домашнее задание, контрольная, КР, экзамен, зачёт, лабораторная, лаба,
дедлайн, deadline, срок сдачи, до, к, assignment, homework, exam, test, quiz, коллоквиум.

Название канала: {channel_name}
{context_block}
Текст поста для анализа:
---
{post_text}
---

Определи предмет по контексту канала (предыдущие посты, название). Если канал явно относится к конкретному предмету — используй его название. Если канал общий (несколько предметов) — определи предмет по содержанию конкретного поста.

Ответь JSON-объектом:
{{
  "has_deadline": true/false,
  "deadlines": [
    {{
      "task_name": "краткое описание задания (например ДЗ 3)",
      "subject": "название курса/предмета, определённое из контекста канала или поста",
      "due_date": "YYYY-MM-DDTHH:MM:SS по московскому времени, или null если неясно",
      "confidence": 0.0-1.0
    }}
  ],
  "reasoning": "краткое объяснение анализа"
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


class HaikuAnalyzer:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if self.api_key:
            self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
        else:
            self.client = None
            logger.warning("ANTHROPIC_API_KEY not set, HaikuAnalyzer disabled")

    async def analyze_post(self, text: str, channel_name: str = "", channel_context: str = "") -> dict:
        if not self.client:
            return {"has_deadline": False, "deadlines": [], "reasoning": "API key not configured"}

        current_year = _get_academic_year()

        context_block = ""
        if channel_context:
            # Trim context to avoid huge prompts
            trimmed = channel_context[:3000]
            context_block = f"\nПредыдущие посты канала (для определения предмета/тематики):\n---\n{trimmed}\n---\n"

        prompt = TELEGRAM_ANALYSIS_PROMPT.format(
            post_text=text,
            channel_name=channel_name,
            current_year=current_year,
            context_block=context_block,
        )

        try:
            response = await self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            return _extract_json(raw)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse Haiku response as JSON: {raw[:300]}")
            return {"has_deadline": False, "deadlines": [], "reasoning": "JSON parse error"}
        except Exception as e:
            logger.error(f"Haiku API error: {e}")
            return {"has_deadline": False, "deadlines": [], "reasoning": str(e)}

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
            response = await self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            data = _extract_json(raw)
            return data.get("deadlines", [])
        except Exception as e:
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
