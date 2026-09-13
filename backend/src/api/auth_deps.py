"""
Autentifikatsiya bilan bog'liq dependency'lar:
- Bot -> Backend so'rovlari uchun ichki secret tekshiruvi
- Mini App -> Backend so'rovlari uchun JWT tekshiruvi
- Guruh ichida admin ekanligini tekshirish
"""

import secrets

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
    if not secrets.compare_digest(x_internal_secret, settings.BOT_INTERNAL_SECRET):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ichki so'rov ruxsatnomasi noto'g'ri",
        )

class Identity:
    """`verify_bot_or_mini_app` natijasi - so'rovni kim yuborganini bildiradi."""

    def __init__(self, is_bot: bool, user_id: int | None = None) -> None:
        self.is_bot = is_bot
        self.user_id = user_id


async def verify_bot_or_mini_app(
    x_internal_secret: str = Header(default="", alias="X-Internal-Secret"),
    x_bot_secret: str = Header(default="", alias="X-Bot-Secret"), # 👈 Bot yuborayotgan header ham qo'shildi
    authorization: str = Header(default=""),
) -> Identity:
    """
    Ikkala mijoz turini ham qabul qiladi:
    - Telegram bot -> `X-Internal-Secret` yoki `X-Bot-Secret` header orqali
    - React Mini App -> `Authorization: Bearer <JWT>` orqali

    `DEV_AUTH_BYPASS=true` bo'lgandagina tekshiruv o'tkazib yuboriladi
    (faqat lokal test uchun - tunnel ochiq bo'lsa hech qachon yoqmang).

    Qaytadi: `Identity` - chaqiruvchi bot ekanligini yoki JWT orqali kelgan
    aniq foydalanuvchi (user_id) ekanligini bildiradi. Router'lar shu
    identity'ni `ensure_actor_owns_telegram_id` / `ensure_actor_can_access_group`
    bilan birga ishlatib, so'rov tanasidagi `telegram_id`/`group_id` bilan
    haqiqiy chaqiruvchi bir xil ekanligini tekshiradi (aks holda boshqa
    foydalanuvchi nomidan amal bajarish - IDOR - mumkin bo'lib qolardi).
    """
    if settings.DEV_AUTH_BYPASS:
        return Identity(is_bot=True)

    # 1. Bot tekshiruvi (Ikkala xil header nomini ham tekshiramiz).
    # compare_digest - taqqoslash vaqti secret'ning to'g'ri qismi uzunligiga
    # bog'liq bo'lib qolmasligi uchun.
    if secrets.compare_digest(x_internal_secret, settings.BOT_INTERNAL_SECRET) or secrets.compare_digest(
        x_bot_secret, settings.BOT_INTERNAL_SECRET
    ):
        return Identity(is_bot=True)

    # 2. Mini App (JWT Token) tekshiruvi
    if authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        try:
            payload = decode_token(token, expected_type="access")
            return Identity(is_bot=False, user_id=int(payload["sub"]))
        except TokenError:
            pass

    # Agar hech biri to'g'ri kelmasa
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Ruxsat yo'q - to'g'ri maxfiy kalit yoki Bearer token kerak",
    )


async def ensure_actor_owns_telegram_id(
    identity: Identity, telegram_id: int, session: AsyncSession
) -> None:
    """
    Mini App (JWT) orqali kirgan foydalanuvchi faqat o'z `telegram_id`i
    nomidan amal bajara olishini ta'minlaydi. Aks holda so'rov tanasidagi
    `telegram_id`ni almashtirib, boshqa (masalan, admin) foydalanuvchi
    nomidan amal bajarish mumkin bo'lib qolardi. Bot so'rovlari (is_bot)
    bundan mustasno - bot foydalanuvchini Telegram orqali allaqachon aniqlagan.
    """
    if identity.is_bot:
        return
    user = await UserRepository(session).get_by_id(identity.user_id)
    if user is None or user.telegram_id != telegram_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Boshqa foydalanuvchi nomidan amal bajarish taqiqlangan",
        )


async def ensure_actor_can_access_group(
    identity: Identity, group_id: int, session: AsyncSession
) -> None:
    """Mini App foydalanuvchisi faqat o'zi a'zo bo'lgan guruh ma'lumotlarini ko'ra oladi."""
    if identity.is_bot:
        return
    user = await UserRepository(session).get_by_id(identity.user_id)
    if user and user.is_super_admin:
        return
    membership = await GroupRepository(session).get_membership(identity.user_id, group_id)
    if membership is None or not membership.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Siz bu guruhga tegishli emassiz",
        )


class CurrentUser:
    def __init__(self, user_id: int, is_super_admin: bool) -> None:
        self.user_id = user_id
        self.is_super_admin = is_super_admin


async def get_current_user(authorization: str = Header(default="")) -> CurrentUser:
    """Mini App so'rovlaridan JWT'ni o'qiydi (`Authorization: Bearer <token>`)."""

    if not authorization.startswith("Bearer "):
        if settings.DEV_AUTH_BYPASS:
            return CurrentUser(user_id=1, is_super_admin=True)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token topilmadi")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_token(token, expected_type="access")
    except TokenError as exc:
        if settings.DEV_AUTH_BYPASS:
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
