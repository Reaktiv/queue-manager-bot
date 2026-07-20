"""
Repository Layer: Jarima (Penalty) bilan ishlash.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..infrastructure.models.task import Penalty, TaskAssignment, TaskCompletion


class PenaltyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_penalty(
        self,
        member_id: int,
        task_id: int,
        assignment_id: int,
        points: int = 1,
        reason: str = "missed_deadline",
    ) -> Penalty:
        penalty = Penalty(
            member_id=member_id,
            task_id=task_id,
            assignment_id=assignment_id,
            points=points,
            reason=reason,
        )
        self._session.add(penalty)
        await self._session.flush()
        return penalty

    async def get_total_penalty(self, member_id: int) -> int:
        stmt = select(func.coalesce(func.sum(Penalty.points), 0)).where(
            Penalty.member_id == member_id
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def count_missed(self, member_id: int) -> int:
        stmt = select(func.count(Penalty.id)).where(Penalty.member_id == member_id)
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def get_completion_stats(self, member_id: int) -> dict:
        total_stmt = select(func.count(TaskAssignment.id)).where(
            TaskAssignment.member_id == member_id
        )
        completed_stmt = select(func.count(TaskAssignment.id)).where(
            TaskAssignment.member_id == member_id, TaskAssignment.status == "completed"
        )
        total = (await self._session.execute(total_stmt)).scalar_one()
        completed = (await self._session.execute(completed_stmt)).scalar_one()
        completion_rate = round((completed / total) * 100, 1) if total else 0.0
        return {"total": total, "completed": completed, "completion_rate": completion_rate}

    async def count_all_completions(self) -> int:
        stmt = select(func.count(TaskCompletion.id))
        result = await self._session.execute(stmt)
        return int(result.scalar_one())
