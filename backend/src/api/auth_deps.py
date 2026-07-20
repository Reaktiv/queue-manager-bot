"""
Autentifikatsiya bilan bog'liq dependency'lar:
- Bot -> Backend so'rovlari uchun ichki secret tekshiruvi
- Mini App -> Backend so'rovlari uchun JWT tekshiruvi
- Guruh ichida admin ekanligini tekshirish
"""

from fastapi import Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.security import TokenError, decode_token
from ..infrastructure.models.group import MemberRole
from ..repositories.group_repository import GroupRepository
from ..repositories.user_repository import UserRepository


async def verify_internal_secret(x_internal_secret: str = Header(default="")) -> None:
    """
    Faqat bizning Telegram bot xizmatimiz chaqira oladigan endpointlar uchun.
    Bot har bir so'rovga `X-Internal-Secret` headerini qo'shadi.
    """
    if x_internal_secret != settings.BOT_INTERNAL_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ichki so'rov ruxsatnomasi noto'g'ri",
        )

async def verify_bot_or_mini_app(
    x_internal_secret: str = Header(default="", alias="X-Internal-Secret"),
    x_bot_secret: str = Header(default="", alias="X-Bot-Secret"), # 👈 Bot yuborayotgan header ham qo'shildi
    authorization: str = Header(default=""),
) -> None:
    """
    Ikkala mijoz turini ham qabul qiladi:
    - Telegram bot -> `X-Internal-Secret` yoki `X-Bot-Secret` header orqali
    - React Mini App -> `Authorization: Bearer <JWT>` orqali

    Development (Lokal test) muhitida tekshiruv avtomatik o'tkazib yuboriladi.
    """
    # 🔴 LOKAL MUHIT UCHUN: Test jarayonida 401 xatolik bermasligi uchun chetlab o'tamiz
    if settings.APP_ENV == "development":
        return

    # 1. Bot tekshiruvi (Ikkala xil header nomini ham tekshiramiz)
    if x_internal_secret == settings.BOT_INTERNAL_SECRET or x_bot_secret == settings.BOT_INTERNAL_SECRET:
        return

    # 2. Mini App (JWT Token) tekshiruvi
    if authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        try:
            decode_token(token, expected_type="access")
            return
        except TokenError:
            pass

    # Agar hech biri to'g'ri kelmasa
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Ruxsat yo'q - to'g'ri maxfiy kalit yoki Bearer token kerak",
    )


class CurrentUser:
    def __init__(self, user_id: int, is_super_admin: bool) -> None:
        self.user_id = user_id
        self.is_super_admin = is_super_admin


async def get_current_user(authorization: str = Header(default="")) -> CurrentUser:
    """Mini App so'rovlaridan JWT'ni o'qiydi (`Authorization: Bearer <token>`)."""

    if not authorization.startswith("Bearer "):
        if settings.APP_ENV == "development":
            return CurrentUser(user_id=1, is_super_admin=True)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token topilmadi")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_token(token, expected_type="access")
    except TokenError as exc:
        if settings.APP_ENV == "development":
            return CurrentUser(user_id=1, is_super_admin=True)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    return CurrentUser(
        user_id=int(payload["sub"]), is_super_admin=bool(payload.get("is_super_admin"))
    )

async def require_super_admin(authorization: str = Header(default="")) -> CurrentUser:
    """
    Mini App'dan JWT orqali kelgan so'rovda foydalanuvchi global Super Admin
    ekanligini tekshiradi. Guruh a'zoligidan mutlaqo mustaqil - Bot Owner roli
    guruhlardan tashqarida ishlaydi.
    """
    resolved_user = await get_current_user(authorization)
    if not resolved_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu amalni faqat Super Admin (Bot Owner) bajara oladi",
        )
    return resolved_user


async def ensure_admin_for_group(user_id: int, group_id: int, session: AsyncSession) -> None:
    """
    Foydalanuvchi shu guruhda ADMIN yoki Super Admin ekanligini tekshiradi.
    Router'lar ichida to'g'ridan-to'g'ri chaqiriladi (session allaqachon mavjud bo'lgani uchun).
    """
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    if user and user.is_super_admin:
        return

    group_repo = GroupRepository(session)
    membership = await group_repo.get_membership(user_id, group_id)
    if membership is None or membership.role != MemberRole.ADMIN or not membership.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu amalni faqat guruh admini bajara oladi",
        )
