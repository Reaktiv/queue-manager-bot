from datetime import datetime, timezone

from bot.utils.datetime_utils import get_local_today_in_timezone


def test_get_local_today_in_timezone_uses_group_timezone():
    now_utc = datetime(2026, 7, 17, 20, 30, tzinfo=timezone.utc)

    local_today = get_local_today_in_timezone("Asia/Tashkent", now_utc)

    assert local_today.isoformat() == "2026-07-18"


def test_get_local_today_in_timezone_falls_back_to_default_timezone():
    now_utc = datetime(2026, 7, 17, 20, 30, tzinfo=timezone.utc)

    local_today = get_local_today_in_timezone("Invalid/Timezone", now_utc)

    assert local_today.isoformat() == "2026-07-18"
