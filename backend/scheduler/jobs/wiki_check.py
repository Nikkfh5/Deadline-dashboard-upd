import asyncio
import logging
from collections import defaultdict
from datetime import datetime

from services.database import get_db
from services.wiki_parser import WikiParser
from services.haiku_analyzer import get_analyzer
from services.deadline_extractor import save_extracted_deadlines

logger = logging.getLogger(__name__)

_parser = None


def _get_parser():
    global _parser
    if _parser is None:
        _parser = WikiParser(haiku_analyzer=get_analyzer())
    return _parser


async def wiki_check_job():
    """Check all active wiki sources for updates."""
    logger.info("Running wiki check job...")
    db = get_db()
    parser = _get_parser()

    sources = await db.sources.find({
        "type": "wiki_page",
        "is_active": True,
    }).to_list(200)

    if not sources:
        return

    # Group sources by URL to avoid duplicate fetches
    url_to_sources = defaultdict(list)
    for s in sources:
        url_to_sources[s["identifier"]].append(s)

    # Process URLs concurrently (max 5 at a time)
    sem = asyncio.Semaphore(5)

    async def process_url(url, url_sources):
        async with sem:
            await _check_url(db, parser, url, url_sources)

    tasks = [process_url(url, srcs) for url, srcs in url_to_sources.items()]
    await asyncio.gather(*tasks, return_exceptions=True)

    logger.info(f"Wiki check complete: processed {len(url_to_sources)} unique URLs")


async def _check_url(db, parser, url, url_sources):
    try:
        result = await parser.parse_page(url)
        new_hash = result["content_hash"]

        # Check if content changed (use first source's hash as reference)
        old_hash = url_sources[0].get("last_content_hash")
        now = datetime.utcnow()

        if old_hash == new_hash:
            source_ids = [s["_id"] for s in url_sources]
            await db.sources.update_many(
                {"_id": {"$in": source_ids}},
                {"$set": {"last_checked_at": now}},
            )
            return

        deadlines = result.get("deadlines", [])
        if deadlines:
            user_ids = list(set(s["user_id"] for s in url_sources))
            source_id = str(url_sources[0]["_id"])

            count, rescheduled = await save_extracted_deadlines(
                user_ids=user_ids,
                extracted=deadlines,
                source_id=source_id,
                source_type="wiki",
                raw_text=url,
            )
            logger.info(f"Wiki {url}: found {len(deadlines)} deadlines, {count} new, {len(rescheduled)} rescheduled")

            # Notify users about new deadlines
            if count > 0:
                from services.notifications import notify_new_deadlines
                subject = result.get("subject", url.split("/")[-1].replace("_", " "))
                await notify_new_deadlines(user_ids, deadlines, f"Wiki: {subject}", count)

            if rescheduled:
                from services.notifications import notify_deadline_moved
                subject = result.get("subject", url.split("/")[-1].replace("_", " "))
                await notify_deadline_moved(user_ids, rescheduled, f"Wiki: {subject}")

        # Update all sources for this URL
        source_ids = [s["_id"] for s in url_sources]
        await db.sources.update_many(
            {"_id": {"$in": source_ids}},
            {"$set": {
                "last_content_hash": new_hash,
                "last_checked_at": now,
                "updated_at": now,
            }},
        )

    except Exception as e:
        logger.error(f"Failed to check wiki {url}: {e}")
