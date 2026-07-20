"""
Service Layer: Vazifa yaratish, tahrirlash va admin navbat amallari
(skip/swap/reset/transfer). Har bir amal audit_log'ga yoziladi.
"""

from ..infrastructure.models.task import Task
from ..repositories.audit_repository import AuditRepository
from ..repositories.group_repository import GroupRepository
from ..repositories.queue_repository import QueueRepository
from ..repositories.task_repository import TaskRepository
from ..repositories.user_repository import UserRepository
from .notification_service import format_telegram_html_mention
from .queue_service import QueueService
from datetime import date, datetime, timedelta, timezone

from ..utils.datetime_utils import (
    calculate_next_reminder_at,
    get_local_today,
    local_date_to_utc_start,
    reminder_window_start_utc,
)


class TaskService:
    def __init__(
        self,
        task_repository: TaskRepository,
        queue_repository: QueueRepository,
        group_repository: GroupRepository,
        audit_repository: AuditRepository,
        assignment_repository=None,
        user_repository: UserRepository | None = None,
        notification_service=None,
    ) -> None:
        self._task_repo = task_repository
        self._queue_repo = queue_repository
        self._group_repo = group_repository
        self._audit_repo = audit_repository
        self._assignment_repo = assignment_repository
        self._user_repo = user_repository
        self._notification_service = notification_service
        self._queue_service = QueueService(queue_repository)

    async def _update_task_next_reminder_at(self, task: Task) -> None:
        group = await self._group_repo.get_by_id(task.group_id)
        next_rem_at = calculate_next_reminder_at(
            now_utc=datetime.now(timezone.utc),
            timezone_str=group.timezone if group else "Asia/Tashkent",
            interval_minutes=task.reminder_interval_minutes,
            start_hour=task.reminder_start_hour,
            end_hour=task.reminder_end_hour
        )
        task.next_reminder_at = next_rem_at

    async def _send_immediate_reminder(self, task: Task, group, now_utc: datetime) -> None:
        if self._notification_service is None or self._user_repo is None:
            return

        current_entry = await self._queue_repo.get_current_entry(task.id)
        if current_entry is None:
            return

        member = await self._group_repo.get_member_by_id(current_entry.member_id)
        if member is None or member.is_on_vacation:
            return

        user = await self._user_repo.get_by_id(member.user_id)
        if user is None:
            return

        text = await self._notification_service.build_message(
            group_id=group.id,
            template_type="reminder",
            language=user.language,
            user=user.full_name,
            task=task.name,
            group=group.name,
        )
        await self._notification_service.send_private_message(user.telegram_id, text)

        if group.telegram_chat_id:
            group_text = await self._notification_service.build_message(
                group_id=group.id,
                template_type="reminder",
                language=user.language,
                user=format_telegram_html_mention(user.full_name, user.telegram_id),
                task=task.name,
                group=group.name,
            )
            await self._notification_service.send_group_message(group.telegram_chat_id, group_text)

        task.next_reminder_at = calculate_next_reminder_at(
            now_utc=now_utc,
            timezone_str=group.timezone,
            interval_minutes=task.reminder_interval_minutes,
            start_hour=task.reminder_start_hour,
            end_hour=task.reminder_end_hour,
        )

    async def _auto_skip_vacationing_members(self, task_id: int) -> None:
        """
        Navbat boshida dam olishdagi (vacation) a'zo tursa, uni avtomatik
        o'tkazib yuboradi. Barcha a'zolar dam olishda bo'lsa - to'xtaydi
        (cheksiz aylanishning oldini olish uchun).
        """
        entries = await self._queue_repo.get_queue_for_task(task_id)
        for _ in range(len(entries)):
            current = await self._queue_repo.get_current_entry(task_id)
            if current is None:
                return
            member = await self._group_repo.get_member_by_id(current.member_id)
            if member is None or not member.is_on_vacation:
                break
            await self._queue_repo.unlock_entry(current.id)
            await self._queue_repo.rotate_queue(task_id)
        await self._queue_service.lock_current_turn(task_id)

    async def create_task_with_queue(
        self,
        group_id: int,
        name: str,
        created_by_user_id: int,
        description: str | None = None,
        schedule_type: str = "daily",
        schedule_interval_days: int | None = None,
        reminder_interval_minutes: int = 60,
        reminder_start_hour: int = 8,
        reminder_end_hour: int = 22,
        require_photo: bool = True,
        priority: int = 0,
        member_ids: list[int] | None = None,
        start_date: date | datetime | None = None,
        next_execution_date = None,
    ) -> Task:
        """
        Yangi vazifa yaratadi va navbatni to'ldiradi.
        Agar `member_ids` berilmasa - guruhning barcha faol a'zolari
        qo'shilish tartibida navbatga qo'yiladi.
        """
        group = await self._group_repo.get_by_id(group_id)
        group_timezone = group.timezone if group else "Asia/Tashkent"
        now_utc = datetime.now(timezone.utc)

        local_today = get_local_today(group_timezone, now_utc)
        if start_date is None:
            start_date_local = local_today
        elif isinstance(start_date, datetime):
            start_date_local = start_date.date()
        else:
            start_date_local = start_date

        start_date_utc = local_date_to_utc_start(start_date_local, group_timezone)
        starts_today_or_past = start_date_local <= local_today

        # schedule_type ni har doim every_x_days qilamiz, faqat schedule_interval_days ishlatiladi
        schedule_type = "every_x_days"
        interval = schedule_interval_days or 1

        if starts_today_or_past:
            next_exec_local = start_date_local + timedelta(days=interval)
        else:
            next_exec_local = start_date_local
        next_exec = local_date_to_utc_start(next_exec_local, group_timezone)

        # Birinchi reminder bugun boshlangan vazifa uchun darhol yuborilsin.
        # Keyingi reminderlar odatdagi vaqt oynasi qoidasi bilan yuradi.
        if starts_today_or_past:
            next_rem_at = now_utc
        else:
            next_rem_at = reminder_window_start_utc(
                local_date=start_date_local,
                timezone_str=group_timezone,
                start_hour=reminder_start_hour,
            )

        task = await self._task_repo.create(
            group_id=group_id,
            name=name,
            description=description,
            created_by_user_id=created_by_user_id,
            schedule_type=schedule_type,
            schedule_interval_days=schedule_interval_days,
            reminder_interval_minutes=reminder_interval_minutes,
            reminder_start_hour=reminder_start_hour,
            reminder_end_hour=reminder_end_hour,
            require_photo=require_photo,
            priority=priority,
            start_date=start_date_utc,
            next_execution_date=next_exec,
            next_reminder_at=next_rem_at,
        )

        if member_ids is None:
            members = await self._group_repo.list_members(group_id)
            member_ids = [m.id for m in members]

        if member_ids:
            await self._task_repo.add_queue_entries(task.id, member_ids)
            await self._queue_service.lock_current_turn(task.id)
            await self._auto_skip_vacationing_members(task.id)

        if starts_today_or_past and self._assignment_repo and member_ids:
            current_entry = await self._queue_repo.get_current_entry(task.id)
            if current_entry is not None:
                await self._assignment_repo.get_or_create_for_local_date(
                    task.id,
                    current_entry.member_id,
                    local_today,
                    group_timezone,
                )
                await self._send_immediate_reminder(task, group, now_utc)

        await self._audit_repo.log(
            action="task_created",
            group_id=group_id,
            user_id=created_by_user_id,
            entity_type="task",
            entity_id=task.id,
            details={"name": name, "members_count": len(member_ids)},
        )
        return task

    async def update_task(self, task_id: int, admin_user_id: int, **fields) -> Task | None:
        task = await self._task_repo.get_by_id(task_id)
        if task is None:
            return None
        updated = await self._task_repo.update(task, **fields)
        await self._audit_repo.log(
            action="task_edited",
            group_id=task.group_id,
            user_id=admin_user_id,
            entity_type="task",
            entity_id=task.id,
            details={k: v for k, v in fields.items() if v is not None},
        )
        return updated

    async def delete_task(self, task_id: int, admin_user_id: int) -> bool:
        task = await self._task_repo.get_by_id(task_id)
        if task is None:
            return False
        await self._task_repo.delete(task)
        await self._audit_repo.log(
            action="task_deleted",
            group_id=task.group_id,
            user_id=admin_user_id,
            entity_type="task",
            entity_id=task.id,
        )
        return True

    async def get_task(self, task_id: int) -> Task | None:
        return await self._task_repo.get_by_id(task_id)

    async def list_group_tasks(self, group_id: int) -> list[Task]:
        return await self._task_repo.list_by_group(group_id)

    async def get_member_tasks(self, member_id: int) -> list[Task]:
        return await self._task_repo.get_tasks_for_member(member_id)

    # --- Admin navbat amallari ---

    async def admin_skip(self, task_id: int, admin_user_id: int) -> None:
        if self._assignment_repo:
            await self._assignment_repo.cancel_uncompleted_assignments(task_id)

        await self._queue_service.admin_skip(task_id)
        await self._auto_skip_vacationing_members(task_id)

        task = await self._task_repo.get_by_id(task_id)
        if task:
            await self._update_task_next_reminder_at(task)

        if self._assignment_repo:
            new_current = await self._queue_repo.get_current_entry(task_id)
            if new_current:
                group = await self._group_repo.get_by_id(task.group_id) if task else None
                timezone_str = group.timezone if group else "Asia/Tashkent"
                await self._assignment_repo.get_or_create_for_local_date(
                    task_id,
                    new_current.member_id,
                    get_local_today(timezone_str),
                    timezone_str,
                )

        await self._audit_repo.log(
            action="queue_updated",
            group_id=task.group_id if task else None,
            user_id=admin_user_id,
            entity_type="task",
            entity_id=task_id,
            details={"operation": "skip"},
        )

    async def admin_swap(
        self, task_id: int, admin_user_id: int, entry_id_a: int, entry_id_b: int
    ) -> None:
        await self._queue_service.admin_swap(task_id, entry_id_a, entry_id_b)
        task = await self._task_repo.get_by_id(task_id)
        await self._audit_repo.log(
            action="queue_updated",
            group_id=task.group_id if task else None,
            user_id=admin_user_id,
            entity_type="task",
            entity_id=task_id,
            details={"operation": "swap", "entry_a": entry_id_a, "entry_b": entry_id_b},
        )

    async def get_queue_preview(self, task_id: int) -> list:
        return await self._queue_service.preview_queue(task_id)

    async def complete_task(
        self, task_id: int, member_id: int, admin_user_id: int | None = None
    ) -> None:
        await self._queue_service.complete_and_advance(task_id)
        await self._auto_skip_vacationing_members(task_id)
        task = await self._task_repo.get_by_id(task_id)
        if task:
            await self._update_task_next_reminder_at(task)
        await self._audit_repo.log(
            action="task_completed" if admin_user_id is None else "admin_force_complete",
            group_id=task.group_id if task else None,
            user_id=admin_user_id,
            entity_type="task",
            entity_id=task_id,
            details={"member_id": member_id},
        )
