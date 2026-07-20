"""
Repository Layer: Group va Member bilan ishlash.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..infrastructure.models.group import Group, Member, MemberRole


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
        await self._session.flush()
        return group

    async def list_members(self, group_id: int) -> list[Member]:
        stmt = (
            select(Member)
            .options(selectinload(Member.user))
            .where(Member.group_id == group_id, Member.is_active.is_(True))
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_membership(self, user_id: int, group_id: int) -> Member | None:
        stmt = select(Member).where(Member.user_id == user_id, Member.group_id == group_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def add_member(
        self, user_id: int, group_id: int, role: MemberRole = MemberRole.MEMBER
    ) -> Member:
        member = Member(user_id=user_id, group_id=group_id, role=role)
        self._session.add(member)
        await self._session.flush()
        return member

    async def get_member_by_id(self, member_id: int) -> Member | None:
        return await self._session.get(Member, member_id)

    async def set_vacation(self, member_id: int, is_on_vacation: bool) -> None:
        member = await self._session.get(Member, member_id)
        if member:
            member.is_on_vacation = is_on_vacation
            await self._session.flush()

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
