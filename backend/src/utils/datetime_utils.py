"""
Sana va vaqt bilan ishlash uchun foydali yordamchi funksiyalar.
"""

import random
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

DEFAULT_TIMEZONE = "Asia/Tashkent"
DEFAULT_ZONEINFO = ZoneInfo(DEFAULT_TIMEZONE)

# Oddiy eslatmalar endi tasodifiy interval o'rniga har kuni qat'iy
# belgilangan shu 3 vaqtda yuboriladi - barcha vazifalar uchun bir xil,
# task darajasida sozlanmaydi.
FIXED_REMINDER_HOURS: tuple[int, ...] = (8, 13, 19)


def get_timezone(timezone_str: str | None) -> ZoneInfo:
    try:
        if timezone_str:
            return ZoneInfo(timezone_str)
    except Exception:
        pass
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


def calculate_next_fixed_reminder_at(
    now_utc: datetime,
    timezone_str: str,
    fixed_hours: tuple[int, ...] = FIXED_REMINDER_HOURS,
) -> datetime:
    """
    Keyingi eslatma vaqtini har kuni qat'iy belgilangan soatlar (standart:
    8:00, 13:00, 19:00) orasidan hisoblab beradi - guruh timezone'i
    bo'yicha bugun hali kelmagan eng yaqin vaqt, yoki barchasi o'tib
    ketgan bo'lsa - ertangi kunning birinchi vaqti.
    """
    tz = get_timezone(timezone_str)
    local_now = ensure_utc(now_utc).astimezone(tz)

    todays_candidates = [
        local_now.replace(hour=h, minute=0, second=0, microsecond=0) for h in fixed_hours
    ]
    upcoming = [c for c in todays_candidates if c > local_now]
    if upcoming:
        candidate = min(upcoming)
    else:
        candidate = (local_now + timedelta(days=1)).replace(
            hour=fixed_hours[0], minute=0, second=0, microsecond=0
        )
    return candidate.astimezone(timezone.utc)


def calculate_next_reminder_at(
    now_utc: datetime,
    timezone_str: str,
    interval_min_minutes: int,
    interval_max_minutes: int,
    start_hour: int,
    end_hour: int,
) -> datetime:
    """
    Keyingi eslatma vaqtini (next_reminder_at) guruh timezone'i va faol soatlari
    (start_hour, end_hour) ni inobatga olgan holda UTC formatida hisoblab beradi.
    Eslatma intervali [interval_min_minutes, interval_max_minutes] oralig'ida
    tasodifiy tanlanadi (min == max bo'lsa - qat'iy interval sifatida ishlaydi).
    """
    tz = get_timezone(timezone_str)
    current_utc = ensure_utc(now_utc)
    local_now = current_utc.astimezone(tz)

    lo, hi = sorted((interval_min_minutes, interval_max_minutes))
    picked_minutes = random.randint(lo, hi) if hi > lo else lo

    if local_now.hour < start_hour:
        candidate = local_now.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    elif local_now.hour >= end_hour:
        candidate = (local_now + timedelta(days=1)).replace(
            hour=start_hour, minute=0, second=0, microsecond=0
        )
    else:
        candidate = local_now + timedelta(minutes=picked_minutes)
        if candidate.hour >= end_hour:
            candidate = (candidate + timedelta(days=1)).replace(
                hour=start_hour, minute=0, second=0, microsecond=0
            )

    return candidate.astimezone(timezone.utc)
