"""
Presentation Layer: Vazifani rasm bilan yakunlash endpointi.

Bot foydalanuvchidan rasm qabul qilib, shu yerga multipart/form-data
sifatida yuboradi.
"""

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel

from ....api.auth_deps import verify_bot_or_mini_app
from ....api.deps import (
    get_completion_service,
    get_group_service,
    get_task_service,
    get_user_service,
)
from ....services.group_service import GroupService
from ....services.photo_completion_service import CompletionService, NotQueueOwnerError
from ....services.task_service import TaskService
from ....services.user_service import UserService

router = APIRouter(
    prefix="/completion", tags=["Task Completion"], dependencies=[Depends(verify_bot_or_mini_app)]
)


class ApiResponse(BaseModel):
    success: bool
    data: object | None = None
    message: str | None = None


@router.post("/{task_id}", response_model=ApiResponse)
async def complete_task_with_photo(
    task_id: int,
    telegram_id: int = Form(...),
    caption: str | None = Form(default=None),
    photo: UploadFile | None = File(default=None),
    task_service: TaskService = Depends(get_task_service),
    user_service: UserService = Depends(get_user_service),
    group_service: GroupService = Depends(get_group_service),
    completion_service: CompletionService = Depends(get_completion_service),
):
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
    except ValueError as exc:
        return ApiResponse(success=False, message=str(exc))

    return ApiResponse(
        success=True,
        data=result,
        message="Vazifa muvaffaqiyatli yakunlandi, navbat yangilandi",
    )
