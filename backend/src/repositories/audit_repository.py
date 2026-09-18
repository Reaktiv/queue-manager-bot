"""
Repository Layer: Audit log yozish.

Qoida: hech qachon audit yozuvini o'chirmaymiz yoki tahrirlamaymiz - faqat qo'shamiz.
"""

import json

from sqlalchemy.ext.asyncio import AsyncSession

from ..infrastructure.models.audit import AuditLog


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def log(
        self,
        action: str,
        group_id: int | None = None,
        user_id: int | None = None,
        entity_type: str | None = None,
        entity_id: int | None = None,
        details: dict | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            action=action,
            group_id=group_id,
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            # `default=str`: ba'zi chaqiruvchilar `details`ga `datetime` kabi
            # to'g'ridan-to'g'ri JSON-serializable bo'lmagan qiymatlar ham
            # uzatadi (masalan `update_task`dagi `next_execution_date`) -
            # audit yozuvi shu sabab butunlay muvaffaqiyatsiz bo'lmasligi
            # kerak, shuning uchun bunday qiymatlar matn ko'rinishiga o'giriladi.
            details=json.dumps(details, ensure_ascii=False, default=str) if details else None,
        )
        self._session.add(entry)
        await self._session.flush()
        return entry
