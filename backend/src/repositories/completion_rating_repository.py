"""
Repository Layer: CompletionRating (guruh a'zolarining sifat bahosi - yulduzlar) bilan ishlash.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..infrastructure.models.task import CompletionRating, TaskCompletion


class CompletionRatingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_rating(
        self, completion_id: int, rater_member_id: int, stars: int
    ) -> CompletionRating:
        """A'zo bahosini yozadi; agar oldin baho bergan bo'lsa - yangilaydi (fikrini o'zgartirishi mumkin)."""
        stmt = select(CompletionRating).where(
            CompletionRating.completion_id == completion_id,
            CompletionRating.rater_member_id == rater_member_id,
        )
        result = await self._session.execute(stmt)
        rating = result.scalar_one_or_none()
        if rating is not None:
            rating.stars = stars
            await self._session.flush()
            return rating

        rating = CompletionRating(
            completion_id=completion_id, rater_member_id=rater_member_id, stars=stars
        )
        self._session.add(rating)
        await self._session.flush()
        return rating

    async def count_and_average_for_completion(self, completion_id: int) -> tuple[int, float]:
        """Bitta topshiriq uchun hozirgacha necha kishi va o'rtacha nechta yulduz berganini qaytaradi."""
        stmt = select(func.count(CompletionRating.id), func.avg(CompletionRating.stars)).where(
            CompletionRating.completion_id == completion_id
        )
        result = await self._session.execute(stmt)
        count, avg = result.one()
        return int(count), round(float(avg), 2) if avg is not None else 0.0

    async def get_average_and_count_for_member(self, member_id: int) -> tuple[float | None, int]:
        """
        A'zo BAJARGAN barcha topshiriqlarga guruhdoshlar bergan yulduzlarning
        o'rtachasi va jami soni. `TaskCompletion.member_id` orqali bog'lanadi -
        rating o'zi kimga emas, QAYSI topshiriqqa berilganini bilади.
        Hech kim baho bermagan bo'lsa (None, 0) qaytadi - RatingService buni
        "hali baho yo'q, standart 5.0 dan boshlanadi" deb talqin qiladi.
        """
        stmt = (
            select(func.count(CompletionRating.id), func.avg(CompletionRating.stars))
            .join(TaskCompletion, CompletionRating.completion_id == TaskCompletion.id)
            .where(TaskCompletion.member_id == member_id)
        )
        result = await self._session.execute(stmt)
        count, avg = result.one()
        if count == 0:
            return None, 0
        return round(float(avg), 2), int(count)
