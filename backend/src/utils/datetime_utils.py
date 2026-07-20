"""
Sana va vaqt bilan ishlash uchun foydali yordamchi funksiyalar.
"""

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

DEFAULT_TIMEZONE = "Asia/Tashkent"
DEFAULT_ZONEINFO = ZoneInfo(DEFAULT_TIMEZONE)


def get_timezone(timezone_str: str | None) -> ZoneInfo:
    return DEFAULT_ZONEINFO


def ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def get_local_today(timezone_str: str, now_utc: datetime | None = None) -> date:
    current_utc = ensure_utc(now_utc or datetime.now(timezone.utc))
    return current_utc.astimezone(get_timezone(timezone_str)).date()


def local_date_to_utc_start(local_date: date, timezone_str: str) -> datetime:
    tz = get_timezone(timezone_str)
    local_dt = datetime.combine(local_date, time.min, tzinfo=tz)
    return local_dt.astimezone(timezone.utc)


def local_date_to_utc_end(local_date: date, timezone_str: str) -> datetime:
    tz = get_timezone(timezone_str)
    local_dt = datetime.combine(local_date, time.max, tzinfo=tz)
    return local_dt.astimezone(timezone.utc)


def utc_to_local_date(dt: datetime, timezone_str: str) -> date:
    return ensure_utc(dt).astimezone(get_timezone(timezone_str)).date()


def reminder_window_start_utc(local_date: date, timezone_str: str, start_hour: int) -> datetime:
    tz = get_timezone(timezone_str)
    local_dt = datetime.combine(
        local_date,
        time(hour=max(0, min(start_hour, 23)), minute=0, second=0, microsecond=0),
        tzinfo=tz,
    )
    return local_dt.astimezone(timezone.utc)


def calculate_next_reminder_at(
    now_utc: datetime,
    timezone_str: str,
    interval_minutes: int,
    start_hour: int,
    end_hour: int,
) -> datetime:
    """
    Keyingi eslatma vaqtini (next_reminder_at) guruh timezone'i va faol soatlari
    (start_hour, end_hour) ni inobatga olgan holda UTC formatida hisoblab beradi.
    """
    tz = get_timezone(timezone_str)
    current_utc = ensure_utc(now_utc)
    local_now = current_utc.astimezone(tz)

    if local_now.hour < start_hour:
        candidate = local_now.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    elif local_now.hour >= end_hour:
        candidate = (local_now + timedelta(days=1)).replace(
            hour=start_hour, minute=0, second=0, microsecond=0
        )
    else:
        candidate = local_now + timedelta(minutes=interval_minutes)
        if candidate.hour >= end_hour:
            candidate = (candidate + timedelta(days=1)).replace(
                hour=start_hour, minute=0, second=0, microsecond=0
            )

    return candidate.astimezone(timezone.utc)
