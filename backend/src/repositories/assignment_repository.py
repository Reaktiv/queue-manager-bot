"""
Repository Layer: TaskAssignment (kunlik tayinlangan vazifa nusxasi) va
TaskCompletion (bajarilgan vazifa tarixi) bilan ishlash.
"""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..infrastructure.models.task import (
    CompletionApprovalStatus,
    Penalty,
    TaskAssignment,
    TaskCompletion,
    TaskStatus,
)
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
        try:
            async with self._session.begin_nested():
                await self._session.flush()
        except IntegrityError:
            # Parallel scheduler jarayoni ayni shu (task_id, member_id, assigned_date)
            # uchun assignment'ni bizdan oldinroq yaratgan bo'lishi mumkin - shu holatda
            # DB unique constraint ishga tushadi va biz allaqachon yaratilgan qatorni qaytaramiz.
            self._session.expunge(assignment)
            result = await self._session.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing is not None:
                return existing
            raise
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

    async def mark_in_progress(self, assignment: TaskAssignment) -> TaskAssignment:
        """Rasm yuborildi, lekin guruh tomonidan hali tasdiqlanmagan."""
        assignment.status = TaskStatus.IN_PROGRESS
        await self._session.flush()
        return assignment

    async def get_by_id(self, assignment_id: int) -> TaskAssignment | None:
        return await self._session.get(TaskAssignment, assignment_id)

    async def cancel_uncompleted_assignments(self, task_id: int) -> None:
        """
        Joriy vazifa uchun barcha bajarilmagan assignmentlarni o'chiradi.

        Diqqat: agar biror assignment uchun allaqachon jarima (Penalty) yozuvi
        yoki TaskCompletion (rasm/ovoz tarixi) mavjud bo'lsa, uni o'chirmaymiz -
        aks holda mos FK cheklovi buzilib IntegrityError chiqadi (masalan, admin
        bir necha kun ketma-ket o'tkazib yuborilgan - va shu sabab jarimalangan -
        vazifani keyinroq "skip" qilsa, yoki a'zo rasm yuborib guruh tasdig'ini
        kutayotgan paytda admin navbatni o'tkazib yuborsa). Bunday qatorlar
        tarix sifatida saqlanib qoladi.
        """
        from sqlalchemy import delete, exists

        penalty_exists = exists().where(Penalty.assignment_id == TaskAssignment.id)
        completion_exists = exists().where(TaskCompletion.assignment_id == TaskAssignment.id)
        stmt = delete(TaskAssignment).where(
            TaskAssignment.task_id == task_id,
            TaskAssignment.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS, TaskStatus.OVERDUE]),
            ~penalty_exists,
            ~completion_exists,
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def get_pending_overdue(self, as_of: datetime) -> list[TaskAssignment]:
        """
        Muddati o'tgan, lekin hali PENDING holatidagi (hali rasm yuborilmagan)
        assignmentlar. IN_PROGRESS (rasm yuborilgan, guruh tasdig'ini kutayotgan)
        assignmentlar bu yerga kirmaydi - a'zo o'z vazifasini vaqtida bajargan,
        faqat tasdiqlash sekin kechayotgan bo'lishi mumkin, uni jarimalash
        adolatsiz bo'lardi.
        """
        stmt = select(TaskAssignment).where(
            TaskAssignment.due_date < as_of,
            TaskAssignment.status == TaskStatus.PENDING,
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def add_completion_record(
        self,
        assignment_id: int,
        member_id: int,
        photo_path: str | None,
        caption: str | None,
        approval_status: CompletionApprovalStatus = CompletionApprovalStatus.PENDING,
    ) -> TaskCompletion:
        completion = TaskCompletion(
            assignment_id=assignment_id,
            member_id=member_id,
            photo_path=photo_path,
            caption=caption,
            approval_status=approval_status,
        )
        self._session.add(completion)
        await self._session.flush()
        return completion

    async def get_pending_completion(self, assignment_id: int) -> TaskCompletion | None:
        """Shu assignment uchun hali guruh tomonidan hal qilinmagan (PENDING) topshiriq bormi."""
        stmt = select(TaskCompletion).where(
            TaskCompletion.assignment_id == assignment_id,
            TaskCompletion.approval_status == CompletionApprovalStatus.PENDING,
        )
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def get_completion_by_id(self, completion_id: int) -> TaskCompletion | None:
        return await self._session.get(TaskCompletion, completion_id)

    async def resolve_completion(
        self, completion: TaskCompletion, approval_status: CompletionApprovalStatus
    ) -> TaskCompletion:
        from datetime import datetime, timezone

        completion.approval_status = approval_status
        completion.resolved_at = datetime.now(timezone.utc)
        await self._session.flush()
        return completion
