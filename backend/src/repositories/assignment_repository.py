"""
Repository Layer: TaskAssignment (kunlik tayinlangan vazifa nusxasi) va
TaskCompletion (bajarilgan vazifa tarixi) bilan ishlash.
"""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..infrastructure.models.task import TaskAssignment, TaskCompletion, TaskStatus
from ..utils.datetime_utils import local_date_to_utc_end, local_date_to_utc_start


class AssignmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create_for_local_date(
        self, task_id: int, member_id: int, local_date: date, timezone_str: str
    ) -> TaskAssignment:
        """Berilgan lokal sana uchun assignment mavjud bo'lsa qaytaradi, bo'lmasa yaratadi."""
        today_start = local_date_to_utc_start(local_date, timezone_str)
        due_date = local_date_to_utc_end(local_date, timezone_str)
        stmt = select(TaskAssignment).where(
            TaskAssignment.task_id == task_id,
            TaskAssignment.member_id == member_id,
            TaskAssignment.assigned_date == today_start,
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        assignment = TaskAssignment(
            task_id=task_id,
            member_id=member_id,
            assigned_date=today_start,
            due_date=due_date,
            status=TaskStatus.PENDING,
        )
        self._session.add(assignment)
        await self._session.flush()
        return assignment

    async def mark_completed(self, assignment: TaskAssignment) -> TaskAssignment:
        now = datetime.now(timezone.utc)
        assignment.status = TaskStatus.COMPLETED
        assignment.completed_at = now
        assignment.completion_duration_seconds = int(
            (now - assignment.assigned_date).total_seconds()
        )
        await self._session.flush()
        return assignment

    async def mark_overdue(self, assignment: TaskAssignment) -> TaskAssignment:
        assignment.status = TaskStatus.OVERDUE
        await self._session.flush()
        return assignment

    async def cancel_uncompleted_assignments(self, task_id: int) -> None:
        """Joriy vazifa uchun barcha bajarilmagan assignmentlarni o'chiradi."""
        from sqlalchemy import delete
        stmt = delete(TaskAssignment).where(
            TaskAssignment.task_id == task_id,
            TaskAssignment.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS, TaskStatus.OVERDUE]),
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def get_pending_overdue(self, as_of: datetime) -> list[TaskAssignment]:
        """Muddati o'tgan, lekin hali PENDING/IN_PROGRESS holatidagi assignmentlar."""
        stmt = select(TaskAssignment).where(
            TaskAssignment.due_date < as_of,
            TaskAssignment.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]),
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def add_completion_record(
        self, assignment_id: int, member_id: int, photo_path: str | None, caption: str | None
    ) -> TaskCompletion:
        completion = TaskCompletion(
            assignment_id=assignment_id,
            member_id=member_id,
            photo_path=photo_path,
            caption=caption,
        )
        self._session.add(completion)
        await self._session.flush()
        return completion
