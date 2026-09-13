"""
Repository Layer: User bilan ishlash (faqat DB, biznes qoidasiz).
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..infrastructure.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> User | None:
        return await self._session.get(User, user_id)

    async def create(
        self, telegram_id: int, full_name: str, username: str | None, language: str
    ) -> User:
        user = User(
            telegram_id=telegram_id,
            full_name=full_name,
            username=username,
            language=language,
        )
        self._session.add(user)
        await self._session.flush()
        return user

    async def update_profile(
        self, user: User, full_name: str, username: str | None, language: str
    ) -> User:
        user.full_name = full_name
        user.username = username
        user.language = language
        await self._session.flush()
        return user

    async def set_super_admin(self, user: User, is_super_admin: bool) -> User:
        user.is_super_admin = is_super_admin
        await self._session.flush()
        return user

    async def set_phone_number(self, user: User, phone_number: str) -> User:
        user.phone_number = phone_number
        await self._session.flush()
        return user

    async def list_all(self, limit: int = 500) -> list[User]:
        stmt = select(User).order_by(User.created_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_all(self) -> int:
        from sqlalchemy import func

        stmt = select(func.count(User.id))
        result = await self._session.execute(stmt)
        return int(result.scalar_one())
