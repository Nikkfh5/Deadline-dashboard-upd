import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from scheduler.jobs.channel_check import channel_join_job
from scheduler.jobs.reminders import reminders_job
from services.notifications import send_pending_notifications

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler = None


def setup_scheduler():
    global _scheduler
    _scheduler = AsyncIOScheduler()

    _scheduler.add_job(
        send_pending_notifications,
        IntervalTrigger(minutes=1),
        id="notifications",
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

    _scheduler.add_job(
        reminders_job,
        IntervalTrigger(minutes=10),
        id="reminders",
        replace_existing=True,
        max_instances=1,
    )

    _scheduler.start()
    logger.info("Scheduler started with notifications (1min), channel_join (5min), reminders (10min) jobs")


def shutdown_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler stopped")
