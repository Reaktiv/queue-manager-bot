"""
JWT access/refresh token yaratish va tekshirish.

Bu tizimda parol bilan login yo'q - foydalanuvchi Telegram orqali
autentifikatsiya qilinadi (Mini App initData yoki bot orqali), so'ng
unga JWT beriladi va Mini App shu tokenni har bir so'rovda ishlatadi.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from jose import JWTError, jwt

from .config import settings


class TokenError(Exception):
    pass


def _create_token(
    subject: str,
    expires_delta: timedelta,
    token_type: Literal["access", "refresh"],
    extra: dict | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: int, is_super_admin: bool = False) -> str:
    return _create_token(
        subject=str(user_id),
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        token_type="access",
        extra={"is_super_admin": is_super_admin},
    )


def create_refresh_token(user_id: int) -> str:
    return _create_token(
        subject=str(user_id),
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        token_type="refresh",
    )


def decode_token(token: str, expected_type: Literal["access", "refresh"] = "access") -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise TokenError("Token yaroqsiz yoki muddati o'tgan") from exc

    if payload.get("type") != expected_type:
        raise TokenError(f"Token turi noto'g'ri, kutilgan: {expected_type}")

    return payload
