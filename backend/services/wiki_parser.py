import asyncio
import hashlib
import logging
import re
from datetime import datetime
from typing import List, Optional

import httpx
from bs4 import BeautifulSoup

from services.haiku_analyzer import HaikuAnalyzer

logger = logging.getLogger(__name__)

DATE_PATTERN = re.compile(r'(\d{1,2})\.(\d{2})(?:\.(\d{2,4}))?,?\s*(\d{2}:\d{2})?')


class WikiParser:
    def __init__(self, haiku_analyzer: Optional[HaikuAnalyzer] = None):
        self.haiku = haiku_analyzer
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30, follow_redirects=True)
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def parse_page(self, url: str) -> dict:
        client = await self._get_client()

        # Retry HTTP fetch with backoff (2 attempts, 3s delay)
        last_exc = None
        for attempt in range(2):
            try:
                response = await client.get(url)
                response.raise_for_status()
                break
            except httpx.HTTPError as exc:
                last_exc = exc
                if attempt < 1:
                    logger.warning(f"Wiki fetch attempt {attempt + 1} failed for {url}: {exc}, retrying in 3s")
                    await asyncio.sleep(3)
        else:
            raise last_exc

        html = response.text
        content_hash = hashlib.sha256(html.encode()).hexdigest()
        soup = BeautifulSoup(html, "html.parser")

        title_tag = soup.find("h1", id="firstHeading")
        subject = _clean_subject(title_tag.get_text(strip=True)) if title_tag else "Unknown"

        tables = soup.find_all("table", class_="wikitable")
        deadlines = []
        for table in tables:
            deadlines.extend(_parse_table(table, subject))

        # Fallback: send only text content to Haiku, not full HTML
        if not deadlines and self.haiku:
            logger.info(f"No tables found, falling back to Haiku for {url}")
            content_div = soup.find("div", id="mw-content-text")
            text_content = content_div.get_text() if content_div else soup.get_text()
            deadlines = await self.haiku.analyze_wiki(text_content[:10000], url)

        return {"deadlines": deadlines, "content_hash": content_hash, "subject": subject}


def _clean_subject(raw: str) -> str:
    cleaned = re.sub(r'\s*\d{4}/\d{2,4}\s*', '', raw)
    cleaned = re.sub(r'\s*\(.*?\)\s*$', '', cleaned)
    return cleaned.strip() or raw


def _parse_table(table, subject: str) -> List[dict]:
    rows = table.find_all("tr")
    if not rows:
        return []

    headers = [cell.get_text(strip=True).lower() for cell in rows[0].find_all(["th", "td"])]

    task_col = _find_column(headers, ["задание", "задача", "assignment", "task", "название"])
    date_col = _find_column(headers, ["дедлайн", "deadline", "срок", "дата", "date"])

    if date_col == -1:
        return []
    if task_col == -1:
        task_col = 0

    deadlines = []
    for row in rows[1:]:
        cells = row.find_all(["td", "th"])
        if len(cells) <= max(task_col, date_col):
            continue

        task_name = cells[task_col].get_text(strip=True)
        date_text = cells[date_col].get_text(strip=True)

        if not task_name or not date_text:
            continue

        parsed_date = _parse_date(date_text)
        if parsed_date:
            deadlines.append({
                "task_name": task_name,
                "subject": subject,
                "due_date": parsed_date.isoformat(),
                "confidence": 0.95,
            })

    return deadlines


def _find_column(headers: List[str], keywords: List[str]) -> int:
    for i, h in enumerate(headers):
        if any(kw in h for kw in keywords):
            return i
    return -1


def _parse_date(text: str) -> Optional[datetime]:
    match = DATE_PATTERN.search(text)
    if not match:
        return None

    day = int(match.group(1))
    month = int(match.group(2))
    year_str = match.group(3)
    time_str = match.group(4)

    if year_str:
        year = int(year_str)
        if year < 100:
            year += 2000
    else:
        now = datetime.now()
        year = now.year
        if month < 9 and now.month >= 9:
            year = now.year + 1
        elif month >= 9 and now.month < 9:
            year = now.year - 1

    hour, minute = 23, 59
    if time_str:
        parts = time_str.split(":")
        hour, minute = int(parts[0]), int(parts[1])

    try:
        return datetime(year, month, day, hour, minute)
    except ValueError:
        return None
