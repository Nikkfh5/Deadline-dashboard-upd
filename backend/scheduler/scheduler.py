import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from scheduler.jobs.wiki_check import wiki_check_job
from scheduler.jobs.channel_check import channel_join_job

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler = None


def setup_scheduler():
    global _scheduler
    _scheduler = AsyncIOScheduler()

    _scheduler.add_job(
        wiki_check_job,
        IntervalTrigger(minutes=60),
        id="wiki_check",
        replace_existing=True,
        max_instances=1,
    )

    _scheduler.add_job(
        channel_join_job,
        IntervalTrigger(minutes=5),
        id="channel_join",
        replace_existing=True,
        max_instances=1,
    )

    _scheduler.start()
    logger.info("Scheduler started with wiki_check (60min) and channel_join (5min) jobs")


def shutdown_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler stopped")
