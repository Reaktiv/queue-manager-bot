"""
JWT token va Telegram Mini App initData validatsiyasi uchun testlar
(bazasiz - sof funksiyalar).
"""

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest

from backend.src.core.config import settings
from backend.src.core.security import TokenError, create_access_token, create_refresh_token, decode_token
from backend.src.core.telegram_auth import InvalidInitDataError, validate_init_data


def test_access_token_roundtrip():
    token = create_access_token(user_id=42, is_super_admin=False)
    payload = decode_token(token, expected_type="access")
    assert payload["sub"] == "42"
    assert payload["is_super_admin"] is False


def test_refresh_token_rejected_as_access_token():
    refresh = create_refresh_token(user_id=42)
    with pytest.raises(TokenError):
        decode_token(refresh, expected_type="access")


def test_invalid_token_raises():
    with pytest.raises(TokenError):
        decode_token("not-a-real-jwt-token", expected_type="access")


def _build_init_data(bot_token: str, user: dict) -> str:
    params = {
        "user": json.dumps(user, separators=(",", ":")),
        "auth_date": str(int(time.time())),
        "query_id": "AAH123",
    }
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    params["hash"] = computed_hash
    return urlencode(params)


def test_valid_init_data_is_accepted(monkeypatch):
    monkeypatch.setattr(settings, "BOT_TOKEN", "test_token_abc")
    init_data = _build_init_data("test_token_abc", {"id": 555, "first_name": "Test"})

    user = validate_init_data(init_data)

    assert user["id"] == 555


def test_tampered_init_data_is_rejected(monkeypatch):
    monkeypatch.setattr(settings, "BOT_TOKEN", "test_token_abc")
    init_data = _build_init_data("test_token_abc", {"id": 555, "first_name": "Test"})
    # Foydalanuvchi ID'sini imzodan keyin o'zgartiramiz (hujum simulyatsiyasi)
    tampered = init_data.replace("555", "999")

    with pytest.raises(InvalidInitDataError):
        validate_init_data(tampered)


def test_wrong_bot_token_is_rejected(monkeypatch):
    monkeypatch.setattr(settings, "BOT_TOKEN", "correct_token")
    init_data = _build_init_data("wrong_token", {"id": 555, "first_name": "Test"})

    with pytest.raises(InvalidInitDataError):
        validate_init_data(init_data)
