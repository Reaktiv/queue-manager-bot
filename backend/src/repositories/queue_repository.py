"""
Repository Layer: TaskQueueEntry uchun ma'lumotlar bilan ishlash.

Bu qatlam faqat DB bilan gaplashadi - hech qanday biznes qoida shu yerda
bo'lmaydi (masalan "kim navbatda" degan qaror Service Layer'da qabul qilinadi).
"""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ..infrastructure.models.task import TaskQueueEntry
from ..infrastructure.models.group import Member


class QueueRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_queue_for_task(self, task_id: int) -> list[TaskQueueEntry]:
        stmt = (
            select(TaskQueueEntry)
            .options(
                joinedload(TaskQueueEntry.member).joinedload(Member.user)
            )
            .where(TaskQueueEntry.task_id == task_id)
            .order_by(TaskQueueEntry.position)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_current_entry(self, task_id: int) -> TaskQueueEntry | None:
        """Navbatning boshidagi (position=0) yozuvini qaytaradi."""
        stmt = select(TaskQueueEntry).where(
            TaskQueueEntry.task_id == task_id, TaskQueueEntry.position == 0
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def lock_entry(self, entry_id: int) -> None:
        stmt = update(TaskQueueEntry).where(TaskQueueEntry.id == entry_id).values(is_locked=True)
        await self._session.execute(stmt)

    async def unlock_entry(self, entry_id: int) -> None:
        stmt = update(TaskQueueEntry).where(TaskQueueEntry.id == entry_id).values(is_locked=False)
        await self._session.execute(stmt)

    async def rotate_queue(self, task_id: int) -> None:
        """
        Navbatni bir pozitsiyaga suradi: 0 -> oxiriga, 1->0, 2->1 ...
        Bajarilgandan keyin chaqiriladi.
        """
        entries = await self.get_queue_for_task(task_id)
        if not entries:
            return
        max_position = len(entries) - 1
        for entry in entries:
            entry.position = max_position if entry.position == 0 else entry.position - 1
        await self._session.flush()

    async def swap_members(self, task_id: int, member_id_a: int, member_id_b: int) -> None:
        """Admin ikkita a'zoni navbatda o'rin almashtiradi."""
        stmt_a = select(TaskQueueEntry).where(
            TaskQueueEntry.task_id == task_id, TaskQueueEntry.member_id == member_id_a
        )
        stmt_b = select(TaskQueueEntry).where(
            TaskQueueEntry.task_id == task_id, TaskQueueEntry.member_id == member_id_b
        )
        res_a = await self._session.execute(stmt_a)
        res_b = await self._session.execute(stmt_b)
        entry_a = res_a.scalar_one_or_none()
        entry_b = res_b.scalar_one_or_none()

        # Agar biror a'zo navbatda yo'q bo'lsa (masalan, keyinchalik qo'shilgan yoki dam olishda bo'lgan),
        # uni navbat oxiriga qo'shib, keyin almashtiramiz.
        if not entry_a or not entry_b:
            from sqlalchemy import func
            max_pos_stmt = select(func.max(TaskQueueEntry.position)).where(TaskQueueEntry.task_id == task_id)
            max_pos_res = await self._session.execute(max_pos_stmt)
            max_pos = max_pos_res.scalar()
            next_pos = (max_pos if max_pos is not None else -1) + 1

            if not entry_a:
                entry_a = TaskQueueEntry(task_id=task_id, member_id=member_id_a, position=next_pos)
                self._session.add(entry_a)
                next_pos += 1
            if not entry_b:
                entry_b = TaskQueueEntry(task_id=task_id, member_id=member_id_b, position=next_pos)
                self._session.add(entry_b)
                
            await self._session.flush()

        entry_a.position, entry_b.position = entry_b.position, entry_a.position
        await self._session.flush()

    async def set_order(self, task_id: int, member_ids_in_order: list[int]) -> None:
        """
        Butun navbatni berilgan a'zolar ro'yxati tartibida qayta o'rnatadi
        (masalan, admin barcha a'zolarni birma-bir tanlab yangi tartib
        belgilaganda). Ro'yxat aynan navbatdagi a'zolarning bir xil
        to'plamidan iborat bo'lishi shart - aks holda hech narsa
        o'zgartirilmaydi va xato qaytariladi.
        """
        entries = await self.get_queue_for_task(task_id)
        entries_by_member = {e.member_id: e for e in entries}

        if len(member_ids_in_order) != len(entries) or set(member_ids_in_order) != set(
            entries_by_member.keys()
        ):
            raise ValueError(
                "Berilgan a'zolar ro'yxati navbatdagi joriy a'zolarga to'liq mos kelmadi"
            )

        for position, member_id in enumerate(member_ids_in_order):
            entries_by_member[member_id].position = position
        await self._session.flush()
