"""
Service Layer: Foydalanuvchi bilan bog'liq biznes qoidalar.

Qoida: telegram_id - asosiy identifikator. Agar foydalanuvchi allaqachon
mavjud bo'lsa, biz uni qayta yaratmaymiz, faqat ma'lumotlarini yangilaymiz
(masalan, username yoki ismini o'zgartirgan bo'lishi mumkin).

Bot Owner (Super Admin): agar telegram_id `SUPER_ADMIN_TELEGRAM_IDS`
ro'yxatida bo'lsa, foydalanuvchi avtomatik ravishda global Super Admin
sifatida belgilanadi - bu guruhlardan tashqarida ishlaydigan yagona rol.
"""

from ..core.config import settings
from ..infrastructure.models.user import User
from ..repositories.user_repository import UserRepository


class UserAlreadyExistsButUpdatedError(Exception):
    """Bu xato emas - shunchaki signal, mavjud user yangilandi."""


class UserService:
    def __init__(self, user_repository: UserRepository) -> None:
        self._repo = user_repository

    async def register_or_update(
        self, telegram_id: int, full_name: str, username: str | None, language: str
    ) -> tuple[User, bool]:
        """
        Returns:
            (user, is_new) - is_new=True bo'lsa, bu birinchi marta ro'yxatdan o'tish.
        """
        is_super_admin = telegram_id in settings.super_admin_ids

        existing = await self._repo.get_by_telegram_id(telegram_id)
        if existing:
            updated = await self._repo.update_profile(existing, full_name, username, language)
            if is_super_admin and not updated.is_super_admin:
                await self._repo.set_super_admin(updated, True)
            return updated, False

        from sqlalchemy.exc import IntegrityError
        try:
            created = await self._repo.create(telegram_id, full_name, username, language)
            if is_super_admin:
                await self._repo.set_super_admin(created, True)
            return created, True
        except IntegrityError:
            await self._repo._session.rollback()
            existing = await self._repo.get_by_telegram_id(telegram_id)
            if existing:
                updated = await self._repo.update_profile(existing, full_name, username, language)
                if is_super_admin and not updated.is_super_admin:
                    await self._repo.set_super_admin(updated, True)
                return updated, False
            raise

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        return await self._repo.get_by_telegram_id(telegram_id)

    async def set_phone_number(self, telegram_id: int, phone_number: str) -> User | None:
        user = await self._repo.get_by_telegram_id(telegram_id)
        if user is None:
            return None
        return await self._repo.set_phone_number(user, phone_number)
