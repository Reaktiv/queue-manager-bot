"""
Service Layer: Foydalanuvchi profilidagi 5 yulduzli daraja.

Qoida (spec bo'yicha, aralash model):
    daraja = clamp(guruhdoshlar bergan o'rtacha ball (hali baho bo'lmasa 5.0
             dan boshlanadi) - jami jarima balli, 1.0, 5.0)

Ya'ni ikki mustaqil signal bitta yakuniy songa birlashadi:
  - Sifat bahosi: har bir TASDIQLANGAN (approved) topshiriqqa guruhdoshlar
    1-5 yulduz bilan baho beradi (CompletionRating). Bir kishi bir
    topshiriqqa faqat bir marta baho beradi, lekin fikrini o'zgartira oladi.
  - Jarima: har bir o'tkazib yuborilgan (overdue) kun uchun -1 (Penalty
    jadvali - bu allaqachon mavjud, RatingService uni qayta ishlatadi,
    alohida "yulduz jarimasi" ustuni ochilmaydi).

Natija 1.0 dan pastga tushmaydi (standart yulduzli reyting konventsiyasi -
"nol yulduz" chalkash) va 5.0 dan oshmaydi.

Baholash oynasi:
    Topshiriq TASDIQLANGANidan (`TaskCompletion.resolved_at`) keyin
    guruhdoshlar faqat 1 SOAT ichida baho bera oladi. Shu vaqt o'tgach
    hech kim yangi baho qo'sha olmaydi - o'sha payt yig'ilgan o'rtacha
    (agar hech kim baho bermagan bo'lsa - baza 5.0) YAKUNIY hisoblanadi.
"""

from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from ..repositories.completion_rating_repository import CompletionRatingRepository
from ..repositories.group_repository import GroupRepository
from ..repositories.penalty_repository import PenaltyRepository

DEFAULT_STARS = Decimal("5.00")
MIN_STARS = Decimal("1.00")
MAX_STARS = Decimal("5.00")

RATING_WINDOW = timedelta(hours=1)
"""Topshiriq tasdiqlangandan keyin baho qabul qilinadigan muddat."""


class SelfRatingError(Exception):
    """A'zo o'zi bajargan vazifaga o'zi baho bera olmaydi."""


class RatingNotAllowedError(Exception):
    """Faqat guruh tomonidan TASDIQLANGAN (approved) topshiriqlarga baho berish mumkin."""


class RatingWindowExpiredError(Exception):
    """Tasdiqlangandan keyin 1 soatlik baholash muddati allaqachon o'tgan."""


def rating_window_closed(resolved_at: datetime | None) -> bool:
    """
    `resolved_at` - topshiriq tasdiqlangan payt (har doim timezone-aware,
    DB'da `DateTime(timezone=True)`). Agar hali resolved bo'lmagan bo'lsa
    (nazariy holat - `submit_rating` buni oldinroq allaqachon rad etadi)
    oyna yopiq deb hisoblanadi, xavfsizlik uchun.
    """
    if resolved_at is None:
        return True
    now = datetime.now(timezone.utc)
    return now - resolved_at > RATING_WINDOW


class RatingService:
    def __init__(
        self,
        rating_repository: CompletionRatingRepository,
        penalty_repository: PenaltyRepository,
        group_repository: GroupRepository,
    ) -> None:
        self._rating_repo = rating_repository
        self._penalty_repo = penalty_repository
        self._group_repo = group_repository

    def _clamp(self, value: Decimal) -> Decimal:
        return max(MIN_STARS, min(MAX_STARS, value)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    async def record_rating(
        self, completion_id: int, rater_member_id: int, rated_member_id: int, stars: int
    ) -> dict:
        """
        Bitta topshiriqqa baho yozadi va bahoni OLGAN a'zoning (`rated_member_id`
        - topshiriqni bajargan kishi, `rater_member_id` emas) yakuniy
        darajasini qayta hisoblaydi. Kim baholanayotgani, o'zi-o'ziga baho
        berish va guruh a'zoligi tekshiruvi `CompletionService.submit_rating`
        tomonidan allaqachon amalga oshirilgan - bu yerda faqat yozish va
        hisoblash bajariladi.
        """
        await self._rating_repo.upsert_rating(completion_id, rater_member_id, stars)
        completion_count, completion_avg = await self._rating_repo.count_and_average_for_completion(
            completion_id
        )
        new_stars = await self.recalculate_and_get(rated_member_id)
        return {
            "completion_rating_count": completion_count,
            "completion_average": completion_avg,
            "member_rating_stars": float(new_stars),
        }

    async def recalculate_and_get(self, member_id: int) -> Decimal:
        """
        Berilgan a'zoning yakuniy darajasini qayta hisoblaydi, keshga
        yozadi va qaytaradi. Yangi baho kelganda yoki yangi jarima
        qo'shilganda chaqiriladi.
        """
        peer_avg, _count = await self._rating_repo.get_average_and_count_for_member(member_id)
        base = Decimal(str(peer_avg)) if peer_avg is not None else DEFAULT_STARS

        total_penalty = await self._penalty_repo.get_total_penalty(member_id)
        final = self._clamp(base - Decimal(total_penalty))

        await self._group_repo.set_rating_stars(member_id, final)
        return final

    async def get_profile_rating(self, member_id: int) -> dict:
        """Profil sahifasi uchun: yakuniy daraja + tarkibiy qismlar (shaffoflik uchun)."""
        peer_avg, rating_count = await self._rating_repo.get_average_and_count_for_member(
            member_id
        )
        total_penalty = await self._penalty_repo.get_total_penalty(member_id)
        final = await self.recalculate_and_get(member_id)
        return {
            "rating_stars": float(final),
            "peer_rating_avg": peer_avg,
            "rating_count": rating_count,
            "penalty_points": total_penalty,
        }
