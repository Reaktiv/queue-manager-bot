"""
Scheduler vazifalari (background jobs).

Bu modul APScheduler tomonidan davriy chaqiriladi. Har bir funksiya
o'zining DB sessiyasini ochadi va yopadi (background job'lar request-scoped
dependency injection'dan foydalana olmaydi).
"""

from datetime import datetime, timezone

import structlog

from ..infrastructure.db.session import async_session_factory
from ..infrastructure.models.group import Group
from ..repositories.assignment_repository import AssignmentRepository
from ..repositories.group_repository import GroupRepository
from ..repositories.notification_repository import NotificationTemplateRepository
from ..repositories.penalty_repository import PenaltyRepository
from ..repositories.queue_repository import QueueRepository
from ..repositories.task_repository import TaskRepository
from ..repositories.user_repository import UserRepository
from ..services.notification_service import NotificationService, format_telegram_html_mention
from ..services.penalty_service import PenaltyService
from ..utils.datetime_utils import (
    DEFAULT_ZONEINFO,
    calculate_next_reminder_at,
    get_local_today,
    local_date_to_utc_start,
    reminder_window_start_utc,
    utc_to_local_date,
)
from sqlalchemy import select

logger = structlog.get_logger()


def _local_hour(group_timezone: str) -> int:
    """Joriy soatni fixed Central Asia timezone bo'yicha qaytaradi."""
    return datetime.now(DEFAULT_ZONEINFO).hour


async def send_reminders() -> None:
    """
    Har bir faol vazifa uchun: agar hozirgi vaqt next_reminder_at dan o'tgan bo'lsa
    va bugungi topshiriq hali bajarilmagan (PENDING) bo'lsa - private va group xabari yuboriladi.
    """
    from datetime import timedelta
    from ..infrastructure.models.task import TaskAssignment, TaskStatus

    async with async_session_factory() as session:
        task_repo = TaskRepository(session)
        queue_repo = QueueRepository(session)
        group_repo = GroupRepository(session)
        user_repo = UserRepository(session)
        template_repo = NotificationTemplateRepository(session)
        notification_service = NotificationService(template_repo)

        now = datetime.now(timezone.utc)

        groups_result = await session.execute(select(Group).where(Group.is_active.is_(True)))
        groups = list(groups_result.scalars().all())

        for group in groups:
            tasks = await task_repo.list_by_group(group.id, active_only=True)
            for task in tasks:
                if task.next_reminder_at is None or now < task.next_reminder_at:
                    continue

                assignment_stmt = (
                    select(TaskAssignment)
                    .where(
                        TaskAssignment.task_id == task.id,
                        TaskAssignment.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS, TaskStatus.OVERDUE]),
                    )
                    .order_by(TaskAssignment.assigned_date.desc())
                    .limit(1)
                )
                assignment_result = await session.execute(assignment_stmt)
                pending_assignment = assignment_result.scalar_one_or_none()
                if pending_assignment is None:
                    continue

                current_entry = await queue_repo.get_current_entry(task.id)
                if current_entry is None or current_entry.member_id != pending_assignment.member_id:
                    continue

                member = await group_repo.get_member_by_id(current_entry.member_id)
                if member is None or member.is_on_vacation:
                    continue

                user = await user_repo.get_by_id(member.user_id)
                if user is None:
                    continue

                text = await notification_service.build_message(
                    group_id=group.id,
                    template_type="reminder",
                    language=user.language,
                    user=user.full_name,
                    task=task.name,
                    group=group.name,
                )

                await notification_service.send_private_message(user.telegram_id, text)
                logger.info("reminder_sent_private", task_id=task.id, user_telegram_id=user.telegram_id)

                if group.telegram_chat_id:
                    group_text = await notification_service.build_message(
                        group_id=group.id,
                        template_type="reminder",
                        language=user.language,
                        user=format_telegram_html_mention(user.full_name, user.telegram_id),
                        task=task.name,
                        group=group.name,
                    )
                    await notification_service.send_group_message(group.telegram_chat_id, group_text)
                    logger.info("reminder_sent_group", task_id=task.id, telegram_chat_id=group.telegram_chat_id)

                next_rem = calculate_next_reminder_at(
                    now_utc=now,
                    timezone_str=group.timezone if group else "Asia/Tashkent",
                    interval_minutes=task.reminder_interval_minutes,
                    start_hour=task.reminder_start_hour,
                    end_hour=task.reminder_end_hour,
                )
                task.next_reminder_at = next_rem

        await session.commit()


async def check_overdue_tasks() -> None:
    """
    Muddati o'tgan (23:59 dan keyin hali bajarilmagan) vazifalarni topib:
    1. Assignment'ni OVERDUE qiladi.
    2. Jarima qo'shadi (+1 ball).
    3. 2+ kun ketma-ket o'tkazib yuborilgan bo'lsa - guruhga ogohlantirish.
    4. Navbat HECH QACHON o'chmaydi - ertaga ham shu a'zoda qoladi
       (Queue Lock saqlanadi, ya'ni hech narsa qilmaymiz - u allaqachon qulflangan).
    """
    async with async_session_factory() as session:
        assignment_repo = AssignmentRepository(session)
        penalty_repo = PenaltyRepository(session)
        penalty_service = PenaltyService(penalty_repo)
        task_repo = TaskRepository(session)
        group_repo = GroupRepository(session)
        user_repo = UserRepository(session)
        template_repo = NotificationTemplateRepository(session)
        notification_service = NotificationService(template_repo)

        now = datetime.now(timezone.utc)
        overdue_assignments = await assignment_repo.get_pending_overdue(now)

        for assignment in overdue_assignments:
            await assignment_repo.mark_overdue(assignment)
            should_warn = await penalty_service.register_missed_day(
                member_id=assignment.member_id,
                task_id=assignment.task_id,
                assignment_id=assignment.id,
            )

            task = await task_repo.get_by_id(assignment.task_id)
            member = await group_repo.get_member_by_id(assignment.member_id)
            if task is None or member is None:
                continue
            user = await user_repo.get_by_id(member.user_id)
            if user is None:
                continue

            text = await notification_service.build_message(
                group_id=task.group_id,
                template_type="overdue",
                language=user.language,
                user=user.full_name,
                task=task.name,
            )
            await notification_service.send_private_message(user.telegram_id, text)

            if should_warn:
                group = await group_repo.get_by_id(task.group_id)
                if group and group.telegram_chat_id:
                    warning_text = await notification_service.build_message(
                        group_id=task.group_id,
                        template_type="penalty",
                        language=user.language,
                        user=format_telegram_html_mention(user.full_name, user.telegram_id),
                        task=task.name,
                    )
                    await notification_service.send_group_message(
                        group.telegram_chat_id, warning_text
                    )

            logger.info(
                "task_marked_overdue", task_id=assignment.task_id, member_id=assignment.member_id
            )

        await session.commit()


async def generate_daily_assignments() -> None:
    """
    Har kuni (masalan, 00:05 da) faol vazifalar uchun bugungi
    assignment'larni oldindan yaratib qo'yadi (agar bugun bajarish kuni bo'lsa).
    """
    from datetime import timedelta

    async with async_session_factory() as session:
        task_repo = TaskRepository(session)
        queue_repo = QueueRepository(session)
        assignment_repo = AssignmentRepository(session)

        groups_result = await session.execute(select(Group).where(Group.is_active.is_(True)))
        groups = list(groups_result.scalars().all())

        now = datetime.now(timezone.utc)

        for group in groups:
            local_today = get_local_today(group.timezone, now)
            tasks = await task_repo.list_by_group(group.id, active_only=True)
            for task in tasks:
                if task.next_execution_date:
                    if local_today < utc_to_local_date(task.next_execution_date, group.timezone):
                        continue

                current_entry = await queue_repo.get_current_entry(task.id)
                if current_entry is None:
                    continue

                await assignment_repo.get_or_create_for_local_date(
                    task.id,
                    current_entry.member_id,
                    local_today,
                    group.timezone,
                )

                interval = task.schedule_interval_days or 1
                next_local_date = local_today + timedelta(days=interval)
                task.next_execution_date = local_date_to_utc_start(next_local_date, group.timezone)

                task.next_reminder_at = reminder_window_start_utc(
                    local_date=local_today,
                    timezone_str=group.timezone,
                    start_hour=task.reminder_start_hour,
                )

        await session.commit()
        logger.info("daily_assignments_generated")


async def send_pre_warnings() -> None:
    """
    Vazifaga 1 kun qolganda foydalanuvchini ogohlantirish xabari yuboriladi.
    Xabar faqat 1 marta, guruhning reminder_start_hour soatida yuboriladi.
    """
    async with async_session_factory() as session:
        task_repo = TaskRepository(session)
        queue_repo = QueueRepository(session)
        group_repo = GroupRepository(session)
        user_repo = UserRepository(session)
        template_repo = NotificationTemplateRepository(session)
        notification_service = NotificationService(template_repo)

        now = datetime.now(timezone.utc)

        groups_result = await session.execute(select(Group).where(Group.is_active.is_(True)))
        groups = list(groups_result.scalars().all())

        for group in groups:
            tz = DEFAULT_ZONEINFO
            local_now = now.astimezone(tz)
            local_hour = local_now.hour

            tasks = await task_repo.list_by_group(group.id, active_only=True)
            for task in tasks:
                if not task.next_execution_date:
                    continue

                # Difference in days
                task_local_exec = task.next_execution_date.astimezone(tz)
                days_left = (task_local_exec.date() - local_now.date()).days

                if days_left == 1:
                    # Check if already sent for this execution date
                    if task.last_pre_warning_sent_date:
                        last_sent_local = task.last_pre_warning_sent_date.astimezone(tz)
                        if last_sent_local.date() == task_local_exec.date():
                            continue

                    # Send at reminder_start_hour (or if we are past it and haven't sent it yet)
                    if local_hour >= task.reminder_start_hour:
                        current_entry = await queue_repo.get_current_entry(task.id)
                        if current_entry is None:
                            continue

                        member = await group_repo.get_member_by_id(current_entry.member_id)
                        if member is None or member.is_on_vacation:
                            continue

                        user = await user_repo.get_by_id(member.user_id)
                        if user is None:
                            continue

                        text = (
                            f"🔔 <b>Eslatma (1 kun oldin):</b>\n\n"
                            f"Ertaga sizning <b>{task.name}</b> vazifasida navbatingiz keladi!"
                        )

                        success = await notification_service.send_private_message(user.telegram_id, text)
                        if success:
                            task.last_pre_warning_sent_date = task.next_execution_date
                            logger.info("pre_warning_sent", task_id=task.id, user_telegram_id=user.telegram_id)

        await session.commit()
