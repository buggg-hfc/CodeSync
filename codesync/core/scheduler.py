from __future__ import annotations
from datetime import datetime
from typing import Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from codesync.utils.logger import logger

_scheduler = BackgroundScheduler(daemon=True)
_started = False


def _ensure_started() -> None:
    global _started
    if not _started:
        _scheduler.start()
        _started = True


def start_interval(job_id: str, seconds: int, callback: Callable) -> None:
    _ensure_started()
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
    logger.info("Scheduled interval job %s every %ds", job_id, seconds)


def start_daily(job_id: str, time_str: str, callback: Callable) -> None:
    """Schedule a daily job at HH:MM."""
    _ensure_started()
    try:
        hour, minute = map(int, time_str.split(":"))
    except (ValueError, AttributeError):
        hour, minute = 2, 0
    if _scheduler.get_job(job_id):
        _scheduler.remove_job(job_id)
    _scheduler.add_job(
        callback,
        trigger=CronTrigger(hour=hour, minute=minute),
        id=job_id,
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=300,
    )
    logger.info("Scheduled daily job %s at %02d:%02d", job_id, hour, minute)


def get_next_run_times_for_config(config_id: str) -> list[datetime]:
    """Return next run times for all jobs belonging to a sync config."""
    prefix = f"sync_{config_id}_"
    result = []
    for job in _scheduler.get_jobs():
        if job.id.startswith(prefix) and job.next_run_time:
            result.append(job.next_run_time)
    return result


def stop_jobs_for_config(config_id: str) -> None:
    prefix = f"sync_{config_id}_"
    for job in _scheduler.get_jobs():
        if job.id.startswith(prefix):
            job.remove()
    logger.info("Stopped all scheduled jobs for config %s", config_id)


def stop(job_id: str) -> None:
    if _scheduler.get_job(job_id):
        _scheduler.remove_job(job_id)
        logger.info("Stopped job %s", job_id)


def stop_all() -> None:
    global _started
    if _started:
        _scheduler.shutdown(wait=False)
        _started = False
