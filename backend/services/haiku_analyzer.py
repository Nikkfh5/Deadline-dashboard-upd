import anthropic
import asyncio
import json
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

TELEGRAM_ANALYSIS_PROMPT = """<role>
Ты — ассистент студента. Извлекаешь дедлайны из постов в Telegram-каналах: ДЗ, контрольные, экзамены, регистрации, записи в слоты — всё, что требует действия к определённому сроку.
</role>

<context>
Сегодня: {today} ({weekday})
Учебный год: {current_year}
Канал: {channel_name}
{description_block}
{subjects_block}
{context_block}
</context>

<post>
{post_text}
</post>

<rules>
ПРИОРИТЕТ ДАТ (критично):
Если в тексте несколько дат — выбирай ту, к которой студенту нужно совершить действие:
- "Запись открывается 30 марта в 17:00, дедлайн записи до 14 мая" → due_date = 30 марта 17:00 (действовать при открытии)
- "ДЗ выдано 20 марта, сдать до 5 апреля" → due_date = 5 апреля 23:59 (дата сдачи)
- "КР пройдёт 15 апреля" → due_date = 15 апреля (дата события)

ДАТЫ:
- Относительные даты от СЕГОДНЯ: "завтра" = +1, "в пятницу" = ближайшая будущая пятница, "через неделю" = +7.
- Год не указан → {current_year}. Дата уже прошла в этом году → следующий.
- Время не указано → ВСЕГДА 23:59 (и для сдачи, и для событий вроде КР/коллоквиума/экзамена). Точное время указано → используй его.
- Все даты в MSK (UTC+3).

ПРЕДМЕТ:
- Если в описании канала указано название предмета → используй его ДОСЛОВНО.
- Если указаны ранее извлечённые предметы — используй ТО ЖЕ название для единообразия.
- Канал одного предмета → используй его название. Общий канал → определи из поста.

ДЕДУПЛИКАЦИЯ:
- Одно действие = один дедлайн. Не дублируй дедлайн только потому что в посте несколько ссылок, форм или вариантов.
  Пример: "Запись на коллоквиум до 14.04" с двумя формами (для 18.04 и для 21.04) → ОДИН дедлайн "Запись на коллоквиум", все ссылки/формы в details.

ЧТО НЕ ИЗВЛЕКАТЬ:
- Прошедшие даты ("вчера был дедлайн").
- Отменённые задания ("ДЗ 5 отменяется").
- Обсуждения без конкретного срока ("скоро будет контрольная").

ПЕРЕНОСЫ:
- "Дедлайн перенесён на 20 апреля" → извлеки НОВУЮ дату. В details укажи старую.

CONFIDENCE:
- 0.9+: явная дата + явное задание
- 0.7-0.8: дата вычислима, задание понятно из контекста
- 0.6: требуется интерпретация
- < 0.6: не включай в результат
</rules>

<examples>
Пост: "ДЗ 3 по линалу сдать до 15 апреля на anytask"
{{"analysis": "Явное задание с конкретной датой и платформой.", "has_deadline": true, "deadlines": [{{"task_name": "ДЗ 3", "subject": "Линейная алгебра", "due_date": "2026-04-15T23:59:00", "confidence": 0.95, "details": "Сдавать на anytask"}}]}}

Пост: "Ребят, скиньте решения до вторника" (канал: "Матан 2 курс")
{{"analysis": "Предметный канал, срок — ближайший вторник.", "has_deadline": true, "deadlines": [{{"task_name": "Решения (задание)", "subject": "Математический анализ", "due_date": "2026-04-01T23:59:00", "confidence": 0.7, "details": ""}}]}}

Пост: "Экзамен был жёсткий, половина группы завалила"
{{"analysis": "Обсуждение прошедшего экзамена, нет будущего срока.", "has_deadline": false, "deadlines": []}}

Пост: "Запись на НЭ открывается 2 апреля в 12:00 МСК. Закрытие записи 10 апреля."
{{"analysis": "Две даты. Студенту критично записаться при открытии 2 апреля.", "has_deadline": true, "deadlines": [{{"task_name": "Запись на НЭ (открытие)", "subject": "определить из контекста канала", "due_date": "2026-04-02T12:00:00", "confidence": 0.9, "details": "Закрытие записи 10 апреля"}}]}}

Пост: "Коллоквиум 18.04 для групп 1,2,5,7 и 21.04 для групп 3,4,6,8. Запись на оба до 14.04 23:59 по ссылкам: form1, form2"
{{"analysis": "Запись объединена (одна дата 14.04). Два коллоквиума с разными датами — два отдельных дедлайна.", "has_deadline": true, "deadlines": [{{"task_name": "Запись на коллоквиум", "subject": "определить из контекста", "due_date": "2026-04-14T23:59:00", "confidence": 0.9, "details": "18.04 группы 1,2,5,7: form1 | 21.04 группы 3,4,6,8: form2"}}, {{"task_name": "Коллоквиум (группы 1,2,5,7)", "subject": "определить из контекста", "due_date": "2026-04-18T23:59:00", "confidence": 0.85, "details": "Очно, аудитория R404"}}, {{"task_name": "Коллоквиум (группы 3,4,6,8)", "subject": "определить из контекста", "due_date": "2026-04-21T23:59:00", "confidence": 0.85, "details": "Очно, аудитория R405"}}]}}
</examples>

<output_format>
СТРОГО валидный JSON. Без markdown, без ```json```, без текста до или после.
{{
  "analysis": "1-2 предложения: что нашёл, как выбрал дату",
  "has_deadline": true/false,
  "deadlines": [
    {{
      "task_name": "краткое название",
      "subject": "предмет",
      "due_date": "YYYY-MM-DDTHH:MM:SS",
      "confidence": 0.0-1.0,
      "details": "ссылки, условия, или пустая строка"
    }}
  ]
}}
</output_format>"""

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

    async def analyze_post(self, text: str, channel_name: str = "", channel_context: str = "",
                           channel_about: str = "", known_subjects: list = None) -> dict:
        if not self.client:
            return {"has_deadline": False, "deadlines": [], "analysis": "API key not configured"}

        current_year = _get_academic_year()

        context_block = ""
        if channel_context:
            trimmed = channel_context[:3000]
            context_block = f"\nПредыдущие посты канала:\n{trimmed}"

        description_block = ""
        if channel_about:
            description_block = f"Описание канала: {channel_about}"

        subjects_block = ""
        if known_subjects:
            subjects_block = f"Ранее извлечённые предметы из этого канала: {', '.join(known_subjects)}"

        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        weekday_names = {
            "Monday": "понедельник", "Tuesday": "вторник", "Wednesday": "среда",
            "Thursday": "четверг", "Friday": "пятница", "Saturday": "суббота", "Sunday": "воскресенье",
        }
        weekday = weekday_names.get(now.strftime("%A"), now.strftime("%A"))

        prompt = TELEGRAM_ANALYSIS_PROMPT.format(
            post_text=text,
            channel_name=channel_name,
            current_year=current_year,
            context_block=context_block,
            description_block=description_block,
            subjects_block=subjects_block,
            today=today,
            weekday=weekday,
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
            return {"has_deadline": False, "deadlines": [], "analysis": str(e)}

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
