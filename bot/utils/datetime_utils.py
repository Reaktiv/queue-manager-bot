from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo


DEFAULT_TIMEZONE = "Asia/Tashkent"
DEFAULT_ZONEINFO = ZoneInfo(DEFAULT_TIMEZONE)


def get_local_today_in_timezone(
    timezone_str: str | None,
    now_utc: datetime | None = None,
) -> date:
    current_utc = now_utc or datetime.now(timezone.utc)
    if current_utc.tzinfo is None:
        current_utc = current_utc.replace(tzinfo=timezone.utc)
    else:
        current_utc = current_utc.astimezone(timezone.utc)

    return current_utc.astimezone(DEFAULT_ZONEINFO).date()
