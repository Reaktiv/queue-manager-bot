"""
Service Layer: Jarima bilan bog'liq biznes qoidalar.

Qoida (spec bo'yicha):
- Har bir o'tkazib yuborilgan kun uchun +1 jarima ball.
- 2 kun ketma-ket o'tkazib yuborilsa - guruhga ogohlantirish yuboriladi
  (bu haqiqiy yuborish NotificationService orqali amalga oshiriladi,
  bu yerda faqat "ogohlantirish kerakmi" degan qaror qabul qilinadi).
"""

from ..repositories.penalty_repository import PenaltyRepository


class PenaltyService:
    def __init__(self, penalty_repository: PenaltyRepository) -> None:
        self._repo = penalty_repository

    async def register_missed_day(self, member_id: int, task_id: int, assignment_id: int) -> bool:
        """
        Vazifa muddati o'tganda chaqiriladi.

        Returns:
            should_warn - True bo'lsa, guruhga ogohlantirish yuborish kerak
            (ketma-ket 2 yoki undan ko'p kun o'tkazib yuborilgan bo'lsa).
        """
        await self._repo.add_penalty(member_id, task_id, assignment_id)
        consecutive_missed = await self._repo.count_consecutive_missed(member_id)
        return consecutive_missed >= 2

    async def get_member_statistics(self, member_id: int) -> dict:
        total_penalty = await self._repo.get_total_penalty(member_id)
        missed_count = await self._repo.count_missed(member_id)
        completion = await self._repo.get_completion_stats(member_id)
        return {
            "current_penalty": total_penalty,
            "total_missed": missed_count,
            **completion,
        }
