"""
Service Layer: Guruh yaratish va a'zolik biznes qoidalari.

Muhim qoidalar:
- Guruh yaratuvchisi avtomatik ADMIN sifatida qo'shiladi.
- Bir xil foydalanuvchi bir guruhga ikki marta qo'shila olmaydi.
- Taklif kodi noyob bo'lishi kerak - to'qnashuv bo'lsa qaytadan generatsiya qilinadi.
"""

from ..infrastructure.models.group import Group, Member, MemberRole
from ..repositories.group_repository import GroupRepository
from ..repositories.task_repository import TaskRepository
from ..repositories.queue_repository import QueueRepository
from ..utils.invite_code import generate_invite_code


class AlreadyMemberError(Exception):
    """Foydalanuvchi allaqachon shu guruh a'zosi."""


class InvalidInviteCodeError(Exception):
    """Taklif kodi topilmadi yoki guruh faol emas."""


class GroupService:
    def __init__(
        self,
        group_repository: GroupRepository,
        task_repository: TaskRepository = None,
        queue_repository: QueueRepository = None,
    ) -> None:
        self._repo = group_repository
        self._task_repo = task_repository
        self._queue_repo = queue_repository

    async def create_group(
        self,
        name: str,
        created_by_user_id: int,
        timezone: str = "Asia/Tashkent",
        telegram_chat_id: int | None = None,
    ) -> Group:
        # Noyob invite_code topilguncha urinamiz (amalda deyarli har doim 1-urinishda topiladi)
        for _ in range(5):
            code = generate_invite_code()
            existing = await self._repo.get_by_invite_code(code)
            if existing is None:
                break
        else:
            raise RuntimeError("Noyob taklif kodi generatsiya qilinmadi, qaytadan urinib ko'ring")

        group = await self._repo.create(
            name=name,
            invite_code=code,
            created_by_user_id=created_by_user_id,
            timezone=timezone,
            telegram_chat_id=telegram_chat_id,
        )
        # Yaratuvchi avtomatik admin bo'ladi
        await self._repo.add_member(
            user_id=created_by_user_id, group_id=group.id, role=MemberRole.ADMIN
        )
        return group

    async def join_by_invite_code(self, user_id: int, invite_code: str) -> Member:
        group = await self._repo.get_by_invite_code(invite_code)
        if group is None:
            raise InvalidInviteCodeError()

        existing_membership = await self._repo.get_membership(user_id, group.id)
        if existing_membership and existing_membership.is_active:
            raise AlreadyMemberError()

        member = await self._repo.add_member(
            user_id=user_id, group_id=group.id, role=MemberRole.MEMBER
        )

        if self._task_repo and self._queue_repo:
            tasks = await self._task_repo.list_by_group(group.id, active_only=True)
            for task in tasks:
                existing_entries = await self._queue_repo.get_queue_for_task(task.id)
                next_position = len(existing_entries)
                await self._task_repo.add_queue_entries(task.id, [member.id], start_position=next_position)

        return member

    async def get_group_by_invite_code(self, invite_code: str) -> Group | None:
        return await self._repo.get_by_invite_code(invite_code)

    async def get_membership(self, user_id: int, group_id: int):
        return await self._repo.get_membership(user_id, group_id)

    async def list_members(self, group_id: int):
        return await self._repo.list_members(group_id)

    async def set_vacation(self, member_id: int, is_on_vacation: bool) -> None:
        await self._repo.set_vacation(member_id, is_on_vacation)

        if is_on_vacation and self._task_repo and self._queue_repo:
            member = await self._repo.get_member_by_id(member_id)
            if member:
                tasks = await self._task_repo.list_by_group(member.group_id, active_only=True)
                
                from ..repositories.audit_repository import AuditRepository
                from ..repositories.assignment_repository import AssignmentRepository
                from .task_service import TaskService
                
                session = self._repo._session
                audit_repo = AuditRepository(session)
                assignment_repo = AssignmentRepository(session)
                
                task_service = TaskService(
                    task_repository=self._task_repo,
                    queue_repository=self._queue_repo,
                    group_repository=self._repo,
                    audit_repository=audit_repo,
                    assignment_repository=assignment_repo,
                )
                
                for task in tasks:
                    current_entry = await self._queue_repo.get_current_entry(task.id)
                    if current_entry and current_entry.member_id == member_id:
                        await task_service.admin_skip(task_id=task.id, admin_user_id=task.created_by_user_id)

    async def get_member_by_id(self, member_id: int) -> Member | None:
        return await self._repo.get_member_by_id(member_id)

    async def list_groups_for_user(self, user_id: int):
        return await self._repo.list_groups_for_user(user_id)
