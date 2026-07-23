"""
Presentation Layer: Guruh admin bildirishnoma shablonlarini
(reminder, completed, penalty, overdue, queue_changed, task_assigned)
sozlashi uchun endpointlar.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ....api.auth_deps import (
    Identity,
    ensure_actor_can_access_group,
    ensure_actor_owns_telegram_id,
    ensure_admin_for_group,
    verify_bot_or_mini_app,
)
from ....api.deps import get_session, get_user_service
from ....repositories.notification_repository import (
    DEFAULT_TEMPLATES,
    NotificationTemplateRepository,
)
from ....services.user_service import UserService

router = APIRouter(
    prefix="/notification-templates",
    tags=["Notification Templates"],
    dependencies=[Depends(verify_bot_or_mini_app)],
)

VALID_TEMPLATE_TYPES = set(DEFAULT_TEMPLATES.keys())


class ApiResponse(BaseModel):
    success: bool
    data: object | None = None
    message: str | None = None


class SetTemplateRequest(BaseModel):
    telegram_id: int
    group_id: int
    template_type: str = Field(
        description="reminder | completed | penalty | overdue | queue_changed | task_assigned"
    )
    text_template: str
    language: str = "uz"


@router.get("/{group_id}", response_model=ApiResponse)
async def list_templates(
    group_id: int,
    language: str = "uz",
    session: AsyncSession = Depends(get_session),
    identity: Identity = Depends(verify_bot_or_mini_app),
):
    """
    Guruhning barcha shablon turlari bo'yicha joriy matnini qaytaradi
    (agar guruh o'ziga xos shablon belgilamagan bo'lsa - standart matn qaytadi).
    """
    await ensure_actor_can_access_group(identity, group_id, session)
    repo = NotificationTemplateRepository(session)
    data = {
        template_type: await repo.get_template(group_id, template_type, language)
        for template_type in VALID_TEMPLATE_TYPES
    }
    return ApiResponse(success=True, data=data)


@router.post("/", response_model=ApiResponse)
async def set_template(
    payload: SetTemplateRequest,
    session: AsyncSession = Depends(get_session),
    user_service: UserService = Depends(get_user_service),
    identity: Identity = Depends(verify_bot_or_mini_app),
):
    if payload.template_type not in VALID_TEMPLATE_TYPES:
        return ApiResponse(
            success=False,
            message=f"Noto'g'ri shablon turi. Ruxsat etilganlar: {', '.join(sorted(VALID_TEMPLATE_TYPES))}",
        )

    await ensure_actor_owns_telegram_id(identity, payload.telegram_id, session)
    user = await user_service.get_by_telegram_id(payload.telegram_id)
    if user is None:
        return ApiResponse(success=False, message="Avval /start orqali ro'yxatdan o'ting")

    await ensure_admin_for_group(user.id, payload.group_id, session)

    repo = NotificationTemplateRepository(session)
    await repo.set_template(
        group_id=payload.group_id,
        template_type=payload.template_type,
        text_template=payload.text_template,
        language=payload.language,
    )
    await session.commit()
    return ApiResponse(success=True, message="Shablon saqlandi")
