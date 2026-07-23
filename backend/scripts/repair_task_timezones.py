"""
Oldingi timezone xatosi bilan yozilgan task sanalarini tuzatish uchun script.

Eski kod `YYYY-MM-DD` ni to'g'ridan-to'g'ri UTC 00:00 sifatida saqlagan.
Aslida bu sana guruhning lokal sanasi bo'lishi kerak edi. Shu script mavjud
yozuvlarni guruh timezone'iga mos UTC instant'ga qayta hisoblaydi.

Standart rejim: dry-run
Amalda yozish uchun: `venv/bin/python backend/scripts/repair_task_timezones.py --apply`
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.infrastructure.db.session import async_session_factory
from src.infrastructure.models.task import Task
from src.utils.datetime_utils import (
    calculate_next_reminder_at,
    get_local_today,
    local_date_to_utc_start,
    reminder_window_start_utc,
    utc_to_local_date,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="O'zgarishlarni DB'ga saqlaydi")
    parser.add_argument("--task-id", type=int, help="Faqat bitta task'ni tuzatish")
    return parser.parse_args()


def normalize_local_date_field(value: datetime | None, timezone_str: str) -> datetime | None:
    if value is None:
        return None
    intended_local_date = value.date()
    return local_date_to_utc_start(intended_local_date, timezone_str)


async def main() -> None:
    args = parse_args()
    now_utc = datetime.now(timezone.utc)

    async with async_session_factory() as session:
        stmt = select(Task).options(selectinload(Task.group))
        if args.task_id:
            stmt = stmt.where(Task.id == args.task_id)
        result = await session.execute(stmt)
        tasks = list(result.scalars().all())

        changed = 0
        for task in tasks:
            group = task.group
            timezone_str = group.timezone if group else "Asia/Tashkent"

            old_start = task.start_date
            old_next_exec = task.next_execution_date
            old_last_pre_warning = task.last_pre_warning_sent_date

            task.start_date = normalize_local_date_field(task.start_date, timezone_str)
            task.next_execution_date = normalize_local_date_field(task.next_execution_date, timezone_str)
            task.last_pre_warning_sent_date = normalize_local_date_field(
                task.last_pre_warning_sent_date, timezone_str
            )

            local_today = get_local_today(timezone_str, now_utc)
            next_exec_local_date = (
                utc_to_local_date(task.next_execution_date, timezone_str)
                if task.next_execution_date
                else local_today
            )

            if task.next_execution_date and next_exec_local_date > local_today:
                task.next_reminder_at = reminder_window_start_utc(
                    next_exec_local_date,
                    timezone_str,
                    task.reminder_start_hour,
                )
            else:
                task.next_reminder_at = calculate_next_reminder_at(
                    now_utc=now_utc,
                    timezone_str=timezone_str,
                    interval_min_minutes=task.reminder_interval_min_minutes,
                    interval_max_minutes=task.reminder_interval_max_minutes,
                    start_hour=task.reminder_start_hour,
                    end_hour=task.reminder_end_hour,
                )

            if (
                task.start_date != old_start
                or task.next_execution_date != old_next_exec
                or task.last_pre_warning_sent_date != old_last_pre_warning
            ):
                changed += 1
                print(
                    f"task={task.id} tz={timezone_str} "
                    f"start: {old_start} -> {task.start_date}, "
                    f"next_exec: {old_next_exec} -> {task.next_execution_date}, "
                    f"next_rem: {task.next_reminder_at}"
                )

        if args.apply:
            await session.commit()
            print(f"Applied changes to {changed} task(s)")
        else:
            await session.rollback()
            print(f"Dry run complete. {changed} task(s) would be updated.")


if __name__ == "__main__":
    asyncio.run(main())
