"""
Presentation Layer: Foydalanuvchi ro'yxatdan o'tish endpointlari.
Bot shu endpointlarga murojaat qiladi.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ....api.auth_deps import verify_bot_or_mini_app
from ....api.deps import get_user_service
from ....services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"], dependencies=[Depends(verify_bot_or_mini_app)])


class RegisterUserRequest(BaseModel):
    telegram_id: int
    full_name: str = Field(min_length=1, max_length=255)
    username: str | None = None
    language: str = "uz"


class UserOut(BaseModel):
    id: int
    telegram_id: int
    full_name: str
    username: str | None
    language: str

    model_config = {"from_attributes": True}


class ApiResponse(BaseModel):
    success: bool
    data: object | None = None
    message: str | None = None


@router.post("/register", response_model=ApiResponse)
async def register_user(
    payload: RegisterUserRequest, service: UserService = Depends(get_user_service)
):
    user, is_new = await service.register_or_update(
        telegram_id=payload.telegram_id,
        full_name=payload.full_name,
        username=payload.username,
        language=payload.language,
    )
    return ApiResponse(
        success=True,
        data=UserOut.model_validate(user).model_dump(),
        message="Yangi foydalanuvchi ro'yxatdan o'tdi" if is_new else "Ma'lumotlar yangilandi",
    )


@router.get("/{telegram_id}", response_model=ApiResponse)
async def get_user(telegram_id: int, service: UserService = Depends(get_user_service)):
    user = await service.get_by_telegram_id(telegram_id)
    if user is None:
        return ApiResponse(success=False, message="Foydalanuvchi topilmadi")
    return ApiResponse(success=True, data=UserOut.model_validate(user).model_dump())
