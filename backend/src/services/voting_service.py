"""
Service Layer: Bajarilgan vazifani guruh a'zolari ✅/❌ ovoz berib
tasdiqlashi (yoki rad etishi).

Qoida:
    Rasm yuklangan zahoti topshiriq PENDING holatida guruhga yuboriladi.
    Bajaruvchidan tashqari FAOL a'zolar (`eligible_total`) orasidan
    KO'PCHILIGI (yarmidan ko'p, `needed = eligible_total // 2 + 1`) "Ha"
    desa - navbat keyingi a'zoga o'tadi. Ko'pchilik "Yo'q" desa - vazifa
    SHU a'zoda qoladi, u qaytadan bajarishi kerak.

    Ovoz berish 2 soat davom etadi (`VOTE_WINDOW`) - shu muddatgacha
    ko'pchilik hosil bo'lmasa, muddat tugagandan keyin yig'ilgan ovozlar
    bo'yicha hal qilinadi: ko'proq "Ha" bo'lsa - tasdiqlanadi, ko'proq
    "Yo'q" bo'lsa - rad etiladi, teng bo'lsa (yoki hech kim ovoz
    bermagan bo'lsa) - "sukut - rozilik" qoidasi bilan tasdiqlanadi.
"""

from datetime import datetime, timedelta, timezone
from typing import Literal

from ..repositories.completion_vote_repository import CompletionVoteRepository

VOTE_WINDOW = timedelta(hours=2)
"""Rasm yuklangandan keyin guruh ovoz bera oladigan muddat."""

Decision = Literal["approved", "rejected"]


class SelfVoteError(Exception):
    """A'zo o'zi bajargan vazifaga o'zi ovoz bera olmaydi."""


class VoteNotAllowedError(Exception):
    """Faqat hali hal qilinmagan (PENDING) topshiriqqa ovoz berish mumkin."""


class VoteWindowExpiredError(Exception):
    """Rasm yuklangandan keyin 2 soatlik ovoz berish muddati allaqachon o'tgan."""


def vote_window_closed(completed_at: datetime | None) -> bool:
    if completed_at is None:
        return True
    now = datetime.now(timezone.utc)
    return now - completed_at > VOTE_WINDOW


def needed_for_majority(eligible_total: int) -> int:
    """Yarmidan ko'p (qat'iy ko'pchilik) uchun kerakli ovozlar soni."""
    return eligible_total // 2 + 1


def decide(eligible_total: int, yes: int, no: int, timed_out: bool = False) -> Decision | None:
    """
    Joriy ovozlar asosida qaror chiqarish mumkinmi - mumkin bo'lsa qaytaradi,
    aks holda (hali ko'pchilik hosil bo'lmagan va muddat tugamagan) `None`.
    """
    needed = needed_for_majority(eligible_total)
    if yes >= needed:
        return "approved"
    if no >= needed:
        return "rejected"
    if timed_out:
        if no > yes:
            return "rejected"
        return "approved"  # ko'proq "Ha", teng yoki hech kim ovoz bermagan - sukut rozilik
    return None


class VotingService:
    def __init__(self, vote_repository: CompletionVoteRepository) -> None:
        self._vote_repo = vote_repository

    async def record_vote(
        self, completion_id: int, voter_member_id: int, approve: bool, eligible_total: int
    ) -> dict:
        await self._vote_repo.upsert_vote(completion_id, voter_member_id, approve)
        yes, no = await self._vote_repo.count_votes(completion_id)
        return {
            "yes": yes,
            "no": no,
            "eligible_total": eligible_total,
            "needed": needed_for_majority(eligible_total),
            "resolution": decide(eligible_total, yes, no),
        }

    async def tally(self, completion_id: int) -> tuple[int, int]:
        return await self._vote_repo.count_votes(completion_id)
