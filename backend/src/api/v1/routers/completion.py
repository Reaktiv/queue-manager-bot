"""
Presentation Layer: Vazifani rasm bilan yakunlash va guruh tasdig'i (voting) endpointlari.

Bot foydalanuvchidan rasm qabul qilib, shu yerga multipart/form-data
sifatida yuboradi. Agar guruhda ovoz bera oladigan boshqa a'zo bo'lsa,
javobda "auto_approved: false" va guruhga yuborish uchun kerakli
ma'lumotlar (completion_id, telegram_chat_id, ...) qaytadi - botning o'zi
rasmni ✅/❌ tugmalar bilan guruhga yuboradi. Guruh a'zolari keyin
`/completion/{completion_id}/vote` orqali ovoz beradi.
"""

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ....api.auth_deps import Identity, ensure_actor_owns_telegram_id, verify_bot_or_mini_app
from ....api.deps import (
    get_completion_service,
    get_group_service,
    get_session,
    get_task_service,
    get_user_service,
)
from ....services.group_service import GroupService
from ....services.photo_completion_service import (
    AlreadyResolvedError,
    CompletionNotFoundError,
    CompletionService,
    NotGroupMemberError,
    NotQueueOwnerError,
    PendingApprovalError,
    SelfVoteError,
)
from ....services.task_service import TaskService
from ....services.user_service import UserService

router = APIRouter(
    prefix="/completion", tags=["Task Completion"], dependencies=[Depends(verify_bot_or_mini_app)]
)


class ApiResponse(BaseModel):
    success: bool
    data: object | None = None
    message: str | None = None


class VoteRequest(BaseModel):
    telegram_id: int
    approve: bool


@router.post("/{task_id}", response_model=ApiResponse)
async def complete_task_with_photo(
    task_id: int,
    telegram_id: int = Form(...),
    caption: str | None = Form(default=None),
    photo: UploadFile | None = File(default=None),
    session: AsyncSession = Depends(get_session),
    task_service: TaskService = Depends(get_task_service),
    user_service: UserService = Depends(get_user_service),
    group_service: GroupService = Depends(get_group_service),
    completion_service: CompletionService = Depends(get_completion_service),
    identity: Identity = Depends(verify_bot_or_mini_app),
):
    await ensure_actor_owns_telegram_id(identity, telegram_id, session)
    user = await user_service.get_by_telegram_id(telegram_id)
    if user is None:
        return ApiResponse(success=False, message="Avval /start orqali ro'yxatdan o'ting")

    task = await task_service.get_task(task_id)
    if task is None:
        return ApiResponse(success=False, message="Vazifa topilmadi")

    membership = await group_service.get_membership(user.id, task.group_id)
    if membership is None:
        return ApiResponse(success=False, message="Siz bu guruh a'zosi emassiz")

    photo_bytes = await photo.read() if photo else None
    photo_filename = photo.filename if photo else None

    try:
        result = await completion_service.complete_with_photo(
            task=task,
            member_id=membership.id,
            photo_bytes=photo_bytes,
            photo_filename=photo_filename,
            caption=caption,
        )
    except NotQueueOwnerError:
        return ApiResponse(
            success=False, message="Hozir navbat sizda emas - vazifani bajara olmaysiz"
        )
    except PendingApprovalError:
        return ApiResponse(
            success=False,
            message="Oldingi rasmingiz hali guruh tomonidan tasdiqlanish jarayonida",
        )
    except ValueError as exc:
        return ApiResponse(success=False, message=str(exc))

    if result.get("auto_approved"):
        message = "Vazifa muvaffaqiyatli yakunlandi, navbat yangilandi"
    else:
        message = "Rasm qabul qilindi, guruh a'zolarining tasdig'i kutilmoqda"

    return ApiResponse(success=True, data=result, message=message)


@router.post("/{completion_id}/vote", response_model=ApiResponse)
async def vote_completion(
    completion_id: int,
    payload: VoteRequest,
    session: AsyncSession = Depends(get_session),
    completion_service: CompletionService = Depends(get_completion_service),
    identity: Identity = Depends(verify_bot_or_mini_app),
):
    await ensure_actor_owns_telegram_id(identity, payload.telegram_id, session)

    try:
        result = await completion_service.register_vote(
            completion_id, payload.telegram_id, payload.approve
        )
    except CompletionNotFoundError:
        return ApiResponse(success=False, message="Topshiriq topilmadi")
    except AlreadyResolvedError:
        return ApiResponse(success=False, message="Bu vazifa allaqachon hal qilingan")
    except SelfVoteError:
        return ApiResponse(
            success=False, message="Siz o'zingiz bajargan vazifaga ovoz bera olmaysiz"
        )
    except NotGroupMemberError:
        return ApiResponse(success=False, message="Siz bu guruh a'zosi emassiz")

    return ApiResponse(success=True, data=result, message="Ovozingiz qabul qilindi")
