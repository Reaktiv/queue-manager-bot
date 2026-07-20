"""
Repository Layer: Bildirishnoma shablonlari bilan ishlash.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..infrastructure.models.audit import NotificationTemplate

DEFAULT_TEMPLATES: dict[str, str] = {
    "reminder": '⏰ Eslatma: {user}, "{task}" vazifasini bajarish vaqti keldi! ({group})',
    "completed": '✅ {user} "{task}" vazifasini muvaffaqiyatli bajardi.',
    "penalty": '⚠️ {user} "{task}" vazifasini muddatida bajarmadi. Jarima ball qo\'shildi.',
    "overdue": '🔴 "{task}" vazifasi muddati o\'tdi va hali ham {user} zimmasida.',
    "queue_changed": '🔄 "{task}" navbati yangilandi. Endi galatda: {user}.',
    "task_assigned": '📋 {user}, sizga "{task}" vazifasi tayinlandi ({date}).',
}


class NotificationTemplateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_template(self, group_id: int, template_type: str, language: str = "uz") -> str:
        stmt = select(NotificationTemplate).where(
            NotificationTemplate.group_id == group_id,
            NotificationTemplate.template_type == template_type,
            NotificationTemplate.language == language,
        )
        result = await self._session.execute(stmt)
        template = result.scalar_one_or_none()
        if template:
            return template.text_template
        return DEFAULT_TEMPLATES.get(template_type, "{user}: {task}")

    async def set_template(
        self, group_id: int, template_type: str, text_template: str, language: str = "uz"
    ) -> NotificationTemplate:
        stmt = select(NotificationTemplate).where(
            NotificationTemplate.group_id == group_id,
            NotificationTemplate.template_type == template_type,
            NotificationTemplate.language == language,
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            existing.text_template = text_template
            await self._session.flush()
            return existing

        new_template = NotificationTemplate(
            group_id=group_id,
            template_type=template_type,
            text_template=text_template,
            language=language,
        )
        self._session.add(new_template)
        await self._session.flush()
        return new_template
