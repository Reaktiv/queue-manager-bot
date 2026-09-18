"""
Scheduler xizmatining kirish nuqtasi (alohida Docker konteyner sifatida ishlaydi).

Celery'ga o'tish oson bo'lishi uchun: har bir job funksiyasi (`jobs.py`)
o'zi holicha, hech qanday APScheduler-specific narsaga bog'liq emas -
faqat oddiy `async def` funksiyalar. Shuning uchun ularni Celery task
sifatida ham bevosita chaqirish mumkin bo'ladi.
"""

import asyncio
import signal

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .jobs import (
    check_overdue_tasks,
    generate_daily_assignments,
    resolve_expired_completion_votes,
    send_pre_warnings,
    send_reminders,
)

logger = structlog.get_logger()


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")

    # Har 1 daqiqada eslatmalarni tekshirish
    scheduler.add_job(
        send_reminders, IntervalTrigger(minutes=1), id="send_reminders", replace_existing=True
    )

    # Har 15 daqiqada 1 kun qolgan ogohlantirishlarni tekshirish
    scheduler.add_job(
        send_pre_warnings, IntervalTrigger(minutes=15), id="send_pre_warnings", replace_existing=True
    )

    # Har 15 daqiqada tekshiradi: lokal vaqt zonasi bo'yicha qaysi guruhlar
    # yangi kunga o'tgan bo'lsa, assignment aynan o'sha paytda yaratiladi.
    scheduler.add_job(
        generate_daily_assignments,
        IntervalTrigger(minutes=15),
        id="generate_daily_assignments",
        replace_existing=True,
    )

    # Overdue tekshiruvi ham tez-tez ishlaydi, chunki deadline har guruh uchun
    # o'z lokal 23:59:59 vaqtida tugaydi.
    scheduler.add_job(
        check_overdue_tasks,
        IntervalTrigger(minutes=15),
        id="check_overdue_tasks",
        replace_existing=True,
    )

    # Ovoz berish oynasi 2 soat - 10 daqiqalik interval aniqlikning yetarli darajasi.
    scheduler.add_job(
        resolve_expired_completion_votes,
        IntervalTrigger(minutes=10),
        id="resolve_expired_completion_votes",
        replace_existing=True,
    )

    return scheduler


async def main() -> None:
    scheduler = create_scheduler()

    scheduler.start()
    logger.info("scheduler_started", jobs=[job.id for job in scheduler.get_jobs()])

    stop_event = asyncio.Event()

    def _handle_stop(*_args) -> None:
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            asyncio.get_running_loop().add_signal_handler(sig, _handle_stop)
        except NotImplementedError:
            pass  # Windows'da signal handler qo'llab-quvvatlanmaydi

    await stop_event.wait()
    scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
