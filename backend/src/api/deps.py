"""
FastAPI uchun umumiy Dependency'lar (DI konteyneri o'rnini bosadi).
"""

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..infrastructure.db.session import get_db_session
from ..repositories.assignment_repository import AssignmentRepository
from ..repositories.audit_repository import AuditRepository
from ..repositories.completion_vote_repository import CompletionVoteRepository
from ..repositories.group_repository import GroupRepository
from ..repositories.notification_repository import NotificationTemplateRepository
from ..repositories.penalty_repository import PenaltyRepository
from ..repositories.queue_repository import QueueRepository
from ..repositories.settings_repository import SettingsRepository
from ..repositories.task_repository import TaskRepository
from ..repositories.user_repository import UserRepository
from ..services.group_service import GroupService
from ..services.notification_service import NotificationService
from ..services.penalty_service import PenaltyService
from ..services.photo_completion_service import CompletionService
from ..services.photo_storage_service import PhotoStorageService
from ..services.queue_service import QueueService
from ..services.super_admin_service import SuperAdminService
from ..services.task_service import TaskService
from ..services.user_service import UserService

from fastapi import Header, HTTPException, status
from ..core.config import settings
import hmac
import hashlib

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db_session():
        yield session


def get_queue_service(session: AsyncSession = Depends(get_session)) -> QueueService:
    return QueueService(QueueRepository(session))


def get_user_service(session: AsyncSession = Depends(get_session)) -> UserService:
    return UserService(UserRepository(session))


def get_group_service(session: AsyncSession = Depends(get_session)) -> GroupService:
    return GroupService(
        group_repository=GroupRepository(session),
        task_repository=TaskRepository(session),
        queue_repository=QueueRepository(session),
    )


def get_task_service(session: AsyncSession = Depends(get_session)) -> TaskService:
    return TaskService(
        task_repository=TaskRepository(session),
        queue_repository=QueueRepository(session),
        group_repository=GroupRepository(session),
        audit_repository=AuditRepository(session),
        assignment_repository=AssignmentRepository(session),
        user_repository=UserRepository(session),
        notification_service=NotificationService(NotificationTemplateRepository(session)),
    )


def get_penalty_service(session: AsyncSession = Depends(get_session)) -> PenaltyService:
    return PenaltyService(PenaltyRepository(session))


def get_notification_service(session: AsyncSession = Depends(get_session)) -> NotificationService:
    return NotificationService(NotificationTemplateRepository(session))


def get_photo_storage_service() -> PhotoStorageService:
    return PhotoStorageService()


def get_completion_service(
    session: AsyncSession = Depends(get_session),
    task_service: TaskService = Depends(get_task_service),
    notification_service: NotificationService = Depends(get_notification_service),
) -> CompletionService:
    return CompletionService(
        assignment_repository=AssignmentRepository(session),
        group_repository=GroupRepository(session),
        task_service=task_service,
        photo_storage=get_photo_storage_service(),
        notification_service=notification_service,
        user_repository=UserRepository(session),
        vote_repository=CompletionVoteRepository(session),
    )


def get_super_admin_service(
    session: AsyncSession = Depends(get_session),
    notification_service: NotificationService = Depends(get_notification_service),
) -> SuperAdminService:
    return SuperAdminService(
        user_repository=UserRepository(session),
        group_repository=GroupRepository(session),
        task_repository=TaskRepository(session),
        penalty_repository=PenaltyRepository(session),
        settings_repository=SettingsRepository(session),
        audit_repository=AuditRepository(session),
        notification_service=notification_service,
    )





# 1. BOT SO'ROVLARINI TEKSHIRISH (X-Bot-Secret orqali)
async def verify_bot_secret(x_bot_secret: str = Header(None, alias="X-Bot-Secret")):
    """
    Botdan kelgan har bir so'rov sarlavhasida (header) maxfiy kalit borligini tekshiradi.
    """
    # Agar header'da kelmasa yoki biz o'rnatgan kalitga mos kelmasa 401 beradi
    if not x_bot_secret or x_bot_secret != settings.BOT_INTERNAL_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bot xavfsizlik kaliti noto'g'ri yoki yuborilmagan!"
        )
    return x_bot_secret


# 2. TELEGRAM WEB APP (MINI APP) VALIDATSIYASI
def verify_telegram_webapp_data(init_data: dict):
    """
    Mini App'dan kelgan initData haqiqiyligini BOT_TOKEN orqali HMAC-SHA256 yordamida tekshiradi.
    """
    # Agarda local muhitda (development) bo'lsak va tekshirishni chetlab o'tmoqchi bo'lsak:
    if settings.APP_ENV == "development":
        return True

    # Real tekshiruv algoritmi (Production uchun)
    if "hash" not in init_data:
        return False

    check_hash = init_data.pop("hash")
    data_check_string = "\n".join([f"{k}={v}" for k, v in sorted(init_data.items())])

    secret_key = hmac.new(b"WebAppData", settings.BOT_TOKEN.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    return calculated_hash == check_hash
