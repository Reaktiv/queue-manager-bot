"""
Service Layer: Navbat bilan bog'liq barcha biznes qoidalar shu yerda.

Muhim qoida (Queue Lock):
    Navbatning boshida turgan a'zo vazifani BAJARMAGUNCHA, keyingi
    a'zoga navbat o'tmaydi. Faqat admin operatsiyalari (skip/move/
    reset/transfer) buni qo'lda o'zgartira oladi.
"""

from ..repositories.queue_repository import QueueRepository


class QueueService:
    def __init__(self, queue_repository: QueueRepository) -> None:
        self._queue_repo = queue_repository

    async def get_current_assignee(self, task_id: int):
        """Hozir navbatda kim turganini qaytaradi."""
        return await self._queue_repo.get_current_entry(task_id)

    async def lock_current_turn(self, task_id: int) -> None:
        """Vazifa boshlanganda (yoki kun boshida) navbatni qulflaydi."""
        entry = await self._queue_repo.get_current_entry(task_id)
        if entry:
            await self._queue_repo.lock_entry(entry.id)

    async def complete_and_advance(self, task_id: int) -> None:
        """
        A'zo vazifani bajarganda chaqiriladi:
        1. Joriy pozitsiyani ochadi (unlock)
        2. Navbatni bir qadam suradi (rotate)
        3. Yangi boshdagi a'zoni qulflaydi
        """
        current = await self._queue_repo.get_current_entry(task_id)
        if current:
            await self._queue_repo.unlock_entry(current.id)

        await self._queue_repo.rotate_queue(task_id)
        await self.lock_current_turn(task_id)

    async def admin_skip(self, task_id: int) -> None:
        """Admin joriy a'zoni o'tkazib yuborishi (masalan, dam olishda bo'lsa)."""
        current = await self._queue_repo.get_current_entry(task_id)
        if current:
            await self._queue_repo.unlock_entry(current.id)

        await self._queue_repo.rotate_queue(task_id)
        await self.lock_current_turn(task_id)

    async def admin_swap(self, task_id: int, entry_id_a: int, entry_id_b: int) -> None:
        await self._queue_repo.swap_members(task_id, entry_id_a, entry_id_b)

    async def preview_queue(self, task_id: int) -> list:
        """Joriy, keyingi va undan keyingi a'zolarni ko'rsatish uchun."""
        entries = await self._queue_repo.get_queue_for_task(task_id)
        return entries[:3]
