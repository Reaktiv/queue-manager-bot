"""
Mini App uchun autentifikatsiya endpointlari.

Oqim:
1. Mini App ochilganda Telegram unga `initData` beradi.
2. Mini App shu `initData`ni shu yerga yuboradi.
3. Backend imzoni tekshiradi (HMAC), foydalanuvchini topadi/yaratadi, JWT beradi.
4. Mini App keyingi barcha so'rovlarda shu JWT'ni ishlatadi.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ....api.deps import get_session, get_user_service
from ....core.security import TokenError, create_access_token, create_refresh_token, decode_token
from ....core.telegram_auth import InvalidInitDataError, validate_init_data
from ....services.user_service import UserService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/auth", tags=["Auth"])


class ApiResponse(BaseModel):
    success: bool
    data: object | None = None
    message: str | None = None


class TelegramLoginRequest(BaseModel):
    init_data: str


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/telegram", response_model=ApiResponse)
async def login_with_telegram(
    payload: TelegramLoginRequest,
    user_service: UserService = Depends(get_user_service),
):
    try:
        tg_user = validate_init_data(payload.init_data)
    except InvalidInitDataError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    full_name = f"{tg_user.get('first_name', '')} {tg_user.get('last_name', '')}".strip()
    user, _ = await user_service.register_or_update(
        telegram_id=tg_user["id"],
        full_name=full_name or "Foydalanuvchi",
        username=tg_user.get("username"),
        language=tg_user.get("language_code", "uz"),
    )

    access_token = create_access_token(user.id, is_super_admin=user.is_super_admin)
    refresh_token = create_refresh_token(user.id)

    return ApiResponse(
        success=True,
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": user.id,
                "telegram_id": user.telegram_id,
                "full_name": user.full_name,
                "language": user.language,
                "is_super_admin": user.is_super_admin,
            },
        },
    )


@router.post("/refresh", response_model=ApiResponse)
async def refresh_access_token(
    payload: RefreshRequest,
    session: AsyncSession = Depends(get_session),
):
    try:
        token_payload = decode_token(payload.refresh_token, expected_type="refresh")
    except TokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    from ....repositories.user_repository import UserRepository

    user = await UserRepository(session).get_by_id(int(token_payload["sub"]))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Foydalanuvchi topilmadi")

    new_access_token = create_access_token(user.id, is_super_admin=user.is_super_admin)
    return ApiResponse(success=True, data={"access_token": new_access_token})
