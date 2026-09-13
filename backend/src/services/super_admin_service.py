"""
Service Layer: Super Admin (Bot Owner) uchun global boshqaruv.

Bu rol guruhlardan tashqarida ishlaydi - u barcha guruhlarni, foydalanuvchilarni
ko'ra oladi, tizim holatini kuzatadi, broadcast yubora oladi va
maintenance mode'ni yoqib/o'chira oladi.
"""

from ..repositories.audit_repository import AuditRepository
from ..repositories.group_repository import GroupRepository
from ..repositories.penalty_repository import PenaltyRepository
from ..repositories.settings_repository import SettingsRepository
from ..repositories.task_repository import TaskRepository
from ..repositories.user_repository import UserRepository
from .notification_service import NotificationService

MAINTENANCE_MODE_KEY = "maintenance_mode"


class SuperAdminService:
    def __init__(
        self,
        user_repository: UserRepository,
        group_repository: GroupRepository,
        task_repository: TaskRepository,
        penalty_repository: PenaltyRepository,
        settings_repository: SettingsRepository,
        audit_repository: AuditRepository,
        notification_service: NotificationService,
    ) -> None:
        self._user_repo = user_repository
        self._group_repo = group_repository
        self._task_repo = task_repository
        self._penalty_repo = penalty_repository
        self._settings_repo = settings_repository
        self._audit_repo = audit_repository
        self._notification_service = notification_service

    async def list_all_groups_with_stats(self) -> list[dict]:
        groups = await self._group_repo.list_all_groups()
        counts = await self._group_repo.count_members_for_groups([g.id for g in groups])
        return [
            {
                "id": group.id,
                "name": group.name,
                "member_count": counts.get(group.id, 0),
                "timezone": group.timezone,
                "is_active": group.is_active,
                "created_at": group.created_at.isoformat(),
            }
            for group in groups
        ]

    async def list_all_users(self) -> list[dict]:
        users = await self._user_repo.list_all()
        return [
            {
                "id": u.id,
                "telegram_id": u.telegram_id,
                "full_name": u.full_name,
                "username": u.username,
                "is_super_admin": u.is_super_admin,
                "is_active": u.is_active,
                "joined_at": u.joined_at.isoformat(),
            }
            for u in users
        ]

    async def get_system_stats(self) -> dict:
        return {
            "total_groups": await self._group_repo.count_all_groups(),
            "total_users": await self._user_repo.count_all(),
            "total_active_tasks": await self._task_repo.count_all_active(),
            "total_completions": await self._penalty_repo.count_all_completions(),
            "maintenance_mode": await self.is_maintenance_mode(),
        }

    async def is_maintenance_mode(self) -> bool:
        value = await self._settings_repo.get(MAINTENANCE_MODE_KEY)
        return value == "true"

    async def set_maintenance_mode(self, enabled: bool, actor_user_id: int) -> None:
        await self._settings_repo.set(MAINTENANCE_MODE_KEY, "true" if enabled else "false")
        await self._audit_repo.log(
            action="maintenance_mode_changed",
            user_id=actor_user_id,
            details={"enabled": enabled},
        )

    async def broadcast_message(self, text: str, actor_user_id: int) -> dict:
        """Barcha ro'yxatdan o'tgan foydalanuvchilarga xabar yuboradi."""
        users = await self._user_repo.list_all(limit=100_000)
        sent_count = 0
        failed_count = 0
        for user in users:
            success = await self._notification_service.send_private_message(user.telegram_id, text)
            if success:
                sent_count += 1
            else:
                failed_count += 1

        await self._audit_repo.log(
            action="broadcast_sent",
            user_id=actor_user_id,
            details={"sent": sent_count, "failed": failed_count, "total": len(users)},
        )
        return {"sent": sent_count, "failed": failed_count, "total": len(users)}

    async def list_recent_error_logs(self, limit: int = 100) -> list[dict]:
        logs = await self._settings_repo.list_logs(limit=limit)
        return [
            {
                "id": log.id,
                "level": log.level,
                "message": log.message,
                "context": log.context,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ]

    async def clear_error_logs(self, actor_user_id: int) -> int:
        """Barcha xato yozuvlarini o'chiradi. Qaytarib bo'lmaydigan amal -
        kim va qachon bajarganini audit_logs'ga yozib qo'yamiz."""
        deleted_count = await self._settings_repo.clear_logs()
        await self._audit_repo.log(
            action="error_logs_cleared",
            user_id=actor_user_id,
            details={"deleted_count": deleted_count},
        )
        return deleted_count
