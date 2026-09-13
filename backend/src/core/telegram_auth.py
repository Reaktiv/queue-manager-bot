"""
Telegram Mini App `initData` ni tekshirish.

Rasmiy algoritm (https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app):
1. `hash` maydonini ajratib olamiz.
2. Qolgan maydonlarni alifbo tartibida "key=value" qilib birlashtiramiz (\n bilan).
3. secret_key = HMAC_SHA256(bot_token, key="WebAppData")
4. hash_hisoblangan = HMAC_SHA256(data_check_string, key=secret_key)
5. hash_hisoblangan == hash bo'lsa - ma'lumot haqiqiy va Telegram tomonidan yuborilgan.
"""

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from .config import settings


class InvalidInitDataError(Exception):
    pass


def validate_init_data(init_data: str, max_age_seconds: int = 86400) -> dict:
    """
    Telegram Mini App yuborgan `initData` qatorini tekshiradi va
    ichidagi `user` obyektini qaytaradi.

    Raises:
        InvalidInitDataError: hash mos kelmasa yoki muddati o'tgan bo'lsa.
    """
    # DIQQAT: bu tarmoq imzoni umuman tekshirmaydi - ya'ni har kim ixtiyoriy
    # `user` yuborib, istalgan odam (jumladan Super Admin) nomidan kira oladi.
    # Faqat imzosiz lokal test uchun; tunnel ochiq bo'lganda hech qachon yoqmang.
    if settings.DEV_AUTH_BYPASS:
        try:
            parsed = dict(parse_qsl(init_data, strict_parsing=True))
            user_raw = parsed.get("user")
            if user_raw:
                return json.loads(user_raw)
        except Exception:
            pass
        return {
            "id": 12345678,
            "first_name": "Mock",
            "last_name": "User",
            "username": "mockuser",
            "language_code": "uz",
        }

    if not settings.BOT_TOKEN:
        # Bu bo'lmasa quyida hash har doim mos kelmaydi va sabab
        # "Imzo mos kelmadi" bo'lib ko'rinadi - aslida sozlama yetishmaydi.
        raise InvalidInitDataError(
            "BOT_TOKEN sozlanmagan - initData imzosini tekshirib bo'lmaydi"
        )

    try:
        parsed = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError as exc:
        raise InvalidInitDataError("initData formati buzuq") from exc

    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise InvalidInitDataError("hash maydoni topilmadi")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))

    secret_key = hmac.new(b"WebAppData", settings.BOT_TOKEN.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise InvalidInitDataError("Imzo (hash) mos kelmadi - ma'lumot ishonchsiz")

    try:
        auth_date = int(parsed.get("auth_date", 0))
    except ValueError as exc:
        raise InvalidInitDataError("auth_date qiymati noto'g'ri") from exc
    if time.time() - auth_date > max_age_seconds:
        raise InvalidInitDataError("initData muddati o'tgan")

    user_raw = parsed.get("user")
    if not user_raw:
        raise InvalidInitDataError("user maydoni topilmadi")

    try:
        return json.loads(user_raw)
    except json.JSONDecodeError as exc:
        raise InvalidInitDataError("user maydoni JSON sifatida o'qilmadi") from exc
