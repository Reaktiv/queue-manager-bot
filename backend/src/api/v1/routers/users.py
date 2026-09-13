"""
Presentation Layer: Foydalanuvchi ro'yxatdan o'tish endpointlari.
Bot shu endpointlarga murojaat qiladi.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ....api.auth_deps import Identity, ensure_actor_owns_telegram_id, verify_bot_or_mini_app
from ....api.deps import get_session, get_user_service
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
    phone_number: str | None = None

    model_config = {"from_attributes": True}


class SetPhoneNumberRequest(BaseModel):
    telegram_id: int
    phone_number: str = Field(min_length=1, max_length=32)


class ApiResponse(BaseModel):
    success: bool
    data: object | None = None
    message: str | None = None


@router.post("/register", response_model=ApiResponse)
async def register_user(
    payload: RegisterUserRequest,
    session: AsyncSession = Depends(get_session),
    service: UserService = Depends(get_user_service),
    identity: Identity = Depends(verify_bot_or_mini_app),
):
    await ensure_actor_owns_telegram_id(identity, payload.telegram_id, session)
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
async def get_user(
    telegram_id: int,
    session: AsyncSession = Depends(get_session),
    service: UserService = Depends(get_user_service),
    identity: Identity = Depends(verify_bot_or_mini_app),
):
    await ensure_actor_owns_telegram_id(identity, telegram_id, session)
    user = await service.get_by_telegram_id(telegram_id)
    if user is None:
        return ApiResponse(success=False, message="Foydalanuvchi topilmadi")
    return ApiResponse(success=True, data=UserOut.model_validate(user).model_dump())


@router.post("/phone", response_model=ApiResponse)
async def set_phone_number(
    payload: SetPhoneNumberRequest,
    session: AsyncSession = Depends(get_session),
    service: UserService = Depends(get_user_service),
    identity: Identity = Depends(verify_bot_or_mini_app),
):
    """
    Bot foydalanuvchi Telegram'ning "kontakt ulashish" tugmasi orqali
    o'z raqamini yuborganda shu yerga saqlaydi. Botlar boshqa birovning
    raqamini so'ray olmaydi - bu har doim foydalanuvchining O'Z raqami.
    """
    await ensure_actor_owns_telegram_id(identity, payload.telegram_id, session)
    user = await service.set_phone_number(payload.telegram_id, payload.phone_number)
    if user is None:
        return ApiResponse(success=False, message="Foydalanuvchi topilmadi")
    return ApiResponse(success=True, data=UserOut.model_validate(user).model_dump())
