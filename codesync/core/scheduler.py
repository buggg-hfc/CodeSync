from __future__ import annotations
from typing import Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from codesync.utils.logger import logger

_scheduler = BackgroundScheduler(daemon=True)
_started = False


def _ensure_started() -> None:
    global _started
    if not _started:
        _scheduler.start()
        _started = True


def start_interval(profile_id: str, seconds: int, callback: Callable) -> None:
    _ensure_started()
    job_id = f"sync_{profile_id}"
    if _scheduler.get_job(job_id):
        _scheduler.remove_job(job_id)
    _scheduler.add_job(
        callback,
        trigger=IntervalTrigger(seconds=seconds),
        id=job_id,
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=30,
    )
    logger.info("Scheduled interval sync for profile %s every %ds", profile_id, seconds)


def stop(profile_id: str) -> None:
    job_id = f"sync_{profile_id}"
    if _scheduler.get_job(job_id):
        _scheduler.remove_job(job_id)
        logger.info("Stopped scheduled sync for profile %s", profile_id)


def stop_all() -> None:
    global _started
    if _started:
        _scheduler.shutdown(wait=False)
        _started = False
