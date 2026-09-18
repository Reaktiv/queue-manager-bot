"""
Repository Layer: CompletionVote (guruh a'zolarining "bajarildimi?" ✅/❌ ovozi) bilan ishlash.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..infrastructure.models.task import CompletionVote


class CompletionVoteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_vote(
        self, completion_id: int, voter_member_id: int, approve: bool
    ) -> CompletionVote:
        """A'zo ovozini yozadi; oldin ovoz bergan bo'lsa - fikrini o'zgartirishi mumkin."""
        stmt = select(CompletionVote).where(
            CompletionVote.completion_id == completion_id,
            CompletionVote.voter_member_id == voter_member_id,
        )
        result = await self._session.execute(stmt)
        vote = result.scalar_one_or_none()
        if vote is not None:
            vote.approve = approve
            await self._session.flush()
            return vote

        vote = CompletionVote(
            completion_id=completion_id, voter_member_id=voter_member_id, approve=approve
        )
        self._session.add(vote)
        await self._session.flush()
        return vote

    async def get_vote(self, completion_id: int, voter_member_id: int) -> CompletionVote | None:
        stmt = select(CompletionVote).where(
            CompletionVote.completion_id == completion_id,
            CompletionVote.voter_member_id == voter_member_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_votes(self, completion_id: int) -> tuple[int, int]:
        """Bitta topshiriq uchun hozirgacha nechta "Ha" va nechta "Yo'q" ovoz berilganini qaytaradi."""
        stmt = select(
            func.count(CompletionVote.id).filter(CompletionVote.approve.is_(True)),
            func.count(CompletionVote.id).filter(CompletionVote.approve.is_(False)),
        ).where(CompletionVote.completion_id == completion_id)
        result = await self._session.execute(stmt)
        yes_count, no_count = result.one()
        return int(yes_count), int(no_count)
