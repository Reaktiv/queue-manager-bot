"""
Repository Layer: CompletionVote (guruh a'zolarining tasdiqlash ovozlari) bilan ishlash.
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
        """A'zo ovozini yozadi; agar oldin ovoz bergan bo'lsa - yangilaydi (fikrini o'zgartirishi mumkin)."""
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

    async def count_votes(self, completion_id: int) -> tuple[int, int]:
        """(ha_soni, yoq_soni) qaytaradi."""
        stmt = (
            select(CompletionVote.approve, func.count(CompletionVote.id))
            .where(CompletionVote.completion_id == completion_id)
            .group_by(CompletionVote.approve)
        )
        result = await self._session.execute(stmt)
        yes_count = 0
        no_count = 0
        for approve, count in result.all():
            if approve:
                yes_count = count
            else:
                no_count = count
        return yes_count, no_count
