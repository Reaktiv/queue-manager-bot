"""
Repository Layer: Group va Member bilan ishlash.
"""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..infrastructure.models.group import Group, Member, MemberRole


class DuplicateActiveMembershipError(Exception):
    """Foydalanuvchi shu guruhda allaqachon faol a'zolikka ega (DB unique constraint)."""


class DuplicateGroupChatIdError(Exception):
    """Berilgan telegram_chat_id allaqachon boshqa guruhga bog'langan (DB unique constraint)."""


class GroupRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_invite_code(self, invite_code: str) -> Group | None:
        stmt = select(Group).where(Group.invite_code == invite_code, Group.is_active.is_(True))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, group_id: int) -> Group | None:
        return await self._session.get(Group, group_id)

    async def create(
        self,
        name: str,
        invite_code: str,
        created_by_user_id: int,
        timezone: str = "Asia/Tashkent",
        telegram_chat_id: int | None = None,
    ) -> Group:
        group = Group(
            name=name,
            telegram_chat_id=telegram_chat_id,
            invite_code=invite_code,
            created_by_user_id=created_by_user_id,
            timezone=timezone,
        )
        self._session.add(group)
        try:
            async with self._session.begin_nested():
                await self._session.flush()
        except IntegrityError as exc:
            if group in self._session:
                self._session.expunge(group)
            if telegram_chat_id is not None:
                raise DuplicateGroupChatIdError() from exc
            raise
        return group

    async def set_telegram_chat_id(self, group_id: int, telegram_chat_id: int) -> None:
        group = await self._session.get(Group, group_id)
        if group is None:
            return
        group.telegram_chat_id = telegram_chat_id
        try:
            async with self._session.begin_nested():
                await self._session.flush()
        except IntegrityError as exc:
            self._session.expire(group)
            raise DuplicateGroupChatIdError() from exc

    async def list_members(self, group_id: int) -> list[Member]:
        stmt = (
            select(Member)
            .options(selectinload(Member.user))
            .where(Member.group_id == group_id, Member.is_active.is_(True))
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_membership(self, user_id: int, group_id: int) -> Member | None:
        """
        Berilgan foydalanuvchi/guruh uchun a'zolikni qaytaradi. `ux_members_user_group_active`
        unique indexi bir vaqtda faqat bitta FAOL a'zolikka kafolat beradi, lekin tarixiy
        (is_active=false) qatorlar ham mavjud bo'lishi mumkin - shuning uchun `scalar_one_or_none`
        o'rniga eng faol/eng yangi qatorni tanlaymiz, aks holda `MultipleResultsFound` xatosi
        chiqib, foydalanuvchi shu guruh bilan bog'liq HAR QANDAY so'rovda 500 olib qolaveradi.
        """
        stmt = (
            select(Member)
            .where(Member.user_id == user_id, Member.group_id == group_id)
            .order_by(Member.is_active.desc(), Member.joined_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def add_member(
        self, user_id: int, group_id: int, role: MemberRole = MemberRole.MEMBER
    ) -> Member:
        member = Member(user_id=user_id, group_id=group_id, role=role)
        self._session.add(member)
        try:
            async with self._session.begin_nested():
                await self._session.flush()
        except IntegrityError as exc:
            self._session.expunge(member)
            raise DuplicateActiveMembershipError() from exc
        return member

    async def get_member_by_id(self, member_id: int) -> Member | None:
        return await self._session.get(Member, member_id)

    async def set_vacation(self, member_id: int, is_on_vacation: bool) -> None:
        member = await self._session.get(Member, member_id)
        if member:
            member.is_on_vacation = is_on_vacation
            await self._session.flush()

    async def set_rating_stars(self, member_id: int, stars: Decimal) -> None:
        """Profildagi yakuniy daraja keshini yangilaydi (RatingService hisoblab beradi)."""
        member = await self._session.get(Member, member_id)
        if member:
            member.rating_stars_cache = stars
            await self._session.flush()

    async def set_role(self, member_id: int, role: MemberRole) -> Member | None:
        member = await self._session.get(Member, member_id)
        if member is None:
            return None
        member.role = role
        await self._session.flush()
        return member

    async def count_admins(self, group_id: int) -> int:
        """Guruhdagi faol ADMIN a'zolar soni - oxirgi adminni tushirib qo'yishning oldini olish uchun."""
        from sqlalchemy import func

        stmt = select(func.count(Member.id)).where(
            Member.group_id == group_id,
            Member.role == MemberRole.ADMIN,
            Member.is_active.is_(True),
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def list_groups_for_user(self, user_id: int) -> list[tuple[Group, Member]]:
        stmt = (
            select(Group, Member)
            .join(Member, Member.group_id == Group.id)
            .where(Member.user_id == user_id, Member.is_active.is_(True), Group.is_active.is_(True))
        )
        result = await self._session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def list_all_groups(self, limit: int = 500) -> list[Group]:
        stmt = select(Group).order_by(Group.created_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_all_groups(self) -> int:
        from sqlalchemy import func

        stmt = select(func.count(Group.id))
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def count_members_in_group(self, group_id: int) -> int:
        from sqlalchemy import func

        stmt = select(func.count(Member.id)).where(
            Member.group_id == group_id, Member.is_active.is_(True)
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def count_members_for_groups(self, group_ids: list[int]) -> dict[int, int]:
        """`count_members_in_group`ning ommaviy (batch) shakli - super admin
        "barcha guruhlar" ro'yxati uchun N ta guruh bo'lsa N ta alohida
        so'rov o'rniga BITTA `GROUP BY` so'rovi bilan hisoblaydi."""
        from sqlalchemy import func

        if not group_ids:
            return {}

        stmt = (
            select(Member.group_id, func.count(Member.id))
            .where(Member.group_id.in_(group_ids), Member.is_active.is_(True))
            .group_by(Member.group_id)
        )
        result = await self._session.execute(stmt)
        return {group_id: count for group_id, count in result.all()}

    async def count_other_active_members(self, group_id: int, exclude_member_id: int) -> int:
        """Vazifani bajargan a'zodan tashqari, sifat bahosi bera oladigan a'zolar soni."""
        from sqlalchemy import func

        stmt = select(func.count(Member.id)).where(
            Member.group_id == group_id,
            Member.is_active.is_(True),
            Member.id != exclude_member_id,
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())
