"""
Repository Layer: Global key-value sozlamalar (masalan, maintenance_mode).
"""

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..infrastructure.models.settings import SystemLog, SystemSetting


class SettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, key: str) -> str | None:
        stmt = select(SystemSetting).where(SystemSetting.key == key)
        result = await self._session.execute(stmt)
        setting = result.scalar_one_or_none()
        return setting.value if setting else None

    async def set(self, key: str, value: str) -> SystemSetting:
        stmt = select(SystemSetting).where(SystemSetting.key == key)
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            existing.value = value
            await self._session.flush()
            return existing

        setting = SystemSetting(key=key, value=value)
        self._session.add(setting)
        await self._session.flush()
        return setting

    async def add_log(self, level: str, message: str, context: str | None = None) -> SystemLog:
        log = SystemLog(level=level, message=message, context=context)
        self._session.add(log)
        await self._session.flush()
        return log

    async def list_logs(self, limit: int = 100) -> list[SystemLog]:
        stmt = select(SystemLog).order_by(SystemLog.created_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def clear_logs(self) -> int:
        """Barcha xato yozuvlarini o'chiradi. Super Admin panelidagi "Xatolar" bo'limi
        uchun - qaytarib bo'lmaydigan amal, o'chirilgan yozuvlar sonini qaytaradi."""
        count_stmt = select(func.count(SystemLog.id))
        total = (await self._session.execute(count_stmt)).scalar_one()
        await self._session.execute(delete(SystemLog))
        await self._session.flush()
        return int(total)
