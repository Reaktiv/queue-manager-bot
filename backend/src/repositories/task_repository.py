"""
Repository Layer: Task uchun to'liq CRUD.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..infrastructure.models.task import Task, TaskQueueEntry


class TaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        group_id: int,
        name: str,
        created_by_user_id: int,
        description: str | None = None,
        schedule_type: str = "daily",
        schedule_interval_days: int | None = None,
        reminder_interval_min_minutes: int = 60,
        reminder_interval_max_minutes: int = 60,
        reminder_start_hour: int = 8,
        reminder_end_hour: int = 22,
        require_photo: bool = True,
        priority: int = 0,
        start_date = None,
        next_execution_date = None,
        next_reminder_at = None,
    ) -> Task:
        task = Task(
            group_id=group_id,
            name=name,
            description=description,
            created_by_user_id=created_by_user_id,
            schedule_type=schedule_type,
            schedule_interval_days=schedule_interval_days,
            reminder_interval_min_minutes=reminder_interval_min_minutes,
            reminder_interval_max_minutes=reminder_interval_max_minutes,
            reminder_start_hour=reminder_start_hour,
            reminder_end_hour=reminder_end_hour,
            require_photo=require_photo,
            priority=priority,
            start_date=start_date,
            next_execution_date=next_execution_date or start_date,
            next_reminder_at=next_reminder_at,
        )
        self._session.add(task)
        await self._session.flush()
        return task

    async def get_by_id(self, task_id: int) -> Task | None:
        return await self._session.get(Task, task_id)

    async def list_by_group(self, group_id: int, active_only: bool = True) -> list[Task]:
        stmt = select(Task).where(Task.group_id == group_id)
        if active_only:
            stmt = stmt.where(Task.is_active.is_(True))
        stmt = stmt.order_by(Task.priority.desc(), Task.created_at)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, task: Task, **fields) -> Task:
        for key, value in fields.items():
            if value is not None and hasattr(task, key):
                setattr(task, key, value)
        await self._session.flush()
        return task

    async def deactivate(self, task: Task) -> None:
        task.is_active = False
        await self._session.flush()

    async def delete(self, task: Task) -> None:
        from ..infrastructure.models.task import (
            CompletionVote,
            TaskAssignment,
            TaskCompletion,
            TaskQueueEntry,
        )
        from sqlalchemy import delete

        # Get all assignment IDs of the task
        assignment_ids_stmt = select(TaskAssignment.id).where(TaskAssignment.task_id == task.id)
        assignment_ids_res = await self._session.execute(assignment_ids_stmt)
        assignment_ids = list(assignment_ids_res.scalars().all())

        if assignment_ids:
            # Get all completion IDs of those assignments
            completion_ids_stmt = select(TaskCompletion.id).where(
                TaskCompletion.assignment_id.in_(assignment_ids)
            )
            completion_ids_res = await self._session.execute(completion_ids_stmt)
            completion_ids = list(completion_ids_res.scalars().all())

            if completion_ids:
                # Delete votes referencing those completions first (FK)
                await self._session.execute(
                    delete(CompletionVote).where(CompletionVote.completion_id.in_(completion_ids))
                )
            # Delete completions of those assignments
            await self._session.execute(
                delete(TaskCompletion).where(TaskCompletion.assignment_id.in_(assignment_ids))
            )
            # Delete assignments themselves
            await self._session.execute(
                delete(TaskAssignment).where(TaskAssignment.id.in_(assignment_ids))
            )

        # Delete queue entries
        await self._session.execute(
            delete(TaskQueueEntry).where(TaskQueueEntry.task_id == task.id)
        )

        # Delete the task itself
        await self._session.delete(task)
        await self._session.flush()

    async def add_queue_entries(
        self, task_id: int, member_ids: list[int], start_position: int = 0
    ) -> list[TaskQueueEntry]:
        entries = [
            TaskQueueEntry(task_id=task_id, member_id=member_id, position=start_position + position)
            for position, member_id in enumerate(member_ids)
        ]
        self._session.add_all(entries)
        await self._session.flush()
        return entries

    async def get_tasks_for_member(self, member_id: int) -> list[Task]:
        """Bu a'zo hozir navbatning boshida turgan barcha vazifalarni qaytaradi."""
        stmt = (
            select(Task)
            .join(TaskQueueEntry, TaskQueueEntry.task_id == Task.id)
            .where(
                TaskQueueEntry.member_id == member_id,
                TaskQueueEntry.position == 0,
                Task.is_active.is_(True),
            )
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_all_active(self) -> int:
        from sqlalchemy import func

        stmt = select(func.count(Task.id)).where(Task.is_active.is_(True))
        result = await self._session.execute(stmt)
        return int(result.scalar_one())
