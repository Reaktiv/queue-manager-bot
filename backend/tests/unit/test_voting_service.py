"""
VotingService uchun testlar - guruh a'zolarining ✅/❌ ovoz berib
topshiriqni tasdiqlashi (yoki rad etishi).

Qoida: bajaruvchidan tashqari faol a'zolarning yarmidan ko'pi (qat'iy
ko'pchilik) "Ha" desa - tasdiqlanadi; yarmidan ko'pi "Yo'q" desa - rad
etiladi. 2 soatlik muddat tugagach, yig'ilgan ovozlar bo'yicha hal
qilinadi (teng yoki hech kim ovoz bermagan bo'lsa - tasdiqlanadi).
"""

from datetime import datetime, timedelta, timezone

from backend.src.infrastructure.models.group import Group, Member, MemberRole
from backend.src.infrastructure.models.task import (
    CompletionApprovalStatus,
    Task,
    TaskAssignment,
    TaskCompletion,
)
from backend.src.infrastructure.models.user import User
from backend.src.repositories.completion_vote_repository import CompletionVoteRepository
from backend.src.services.voting_service import (
    VOTE_WINDOW,
    VotingService,
    decide,
    needed_for_majority,
    vote_window_closed,
)

# DIQQAT: bu yerda pastdagi sinov funksiyalarining ba'zilari SYNC (masalan,
# `decide` sof funksiya) - `pytestmark = pytest.mark.asyncio` modul darajasida
# qo'yilsa, pytest-asyncio ularga ham nisbatan ogohlantirish chiqaradi.
# `pytest.ini`dagi `asyncio_mode = auto` allaqachon `async def` testlarni
# o'zi aniqlaydi, shuning uchun bu yerda alohida belgi shart emas.


def test_needed_for_majority_is_strict():
    assert needed_for_majority(1) == 1
    assert needed_for_majority(2) == 2
    assert needed_for_majority(3) == 2
    assert needed_for_majority(4) == 3
    assert needed_for_majority(5) == 3


def test_decide_resolves_as_soon_as_majority_reached():
    assert decide(eligible_total=4, yes=3, no=0) == "approved"
    assert decide(eligible_total=4, yes=0, no=3) == "rejected"
    assert decide(eligible_total=4, yes=2, no=1) is None  # hali ko'pchilik yo'q


def test_decide_without_timeout_never_resolves_on_tie():
    assert decide(eligible_total=4, yes=2, no=2) is None


def test_decide_on_timeout_uses_whoever_has_more_votes():
    assert decide(eligible_total=5, yes=2, no=1, timed_out=True) == "approved"
    assert decide(eligible_total=5, yes=1, no=2, timed_out=True) == "rejected"


def test_decide_on_timeout_tie_or_silence_defaults_to_approved():
    assert decide(eligible_total=4, yes=1, no=1, timed_out=True) == "approved"
    assert decide(eligible_total=4, yes=0, no=0, timed_out=True) == "approved"


def test_vote_window_closed():
    now = datetime.now(timezone.utc)
    assert vote_window_closed(None) is True
    assert vote_window_closed(now) is False
    assert vote_window_closed(now - VOTE_WINDOW - timedelta(minutes=1)) is True
    assert vote_window_closed(now - timedelta(minutes=59)) is False


async def _setup_group_with_completion(session, member_count: int = 3):
    owner = User(telegram_id=9100, full_name="Owner")
    session.add(owner)
    await session.flush()

    group = Group(name="Vote Group", invite_code="VOTETEST", created_by_user_id=owner.id)
    session.add(group)
    await session.flush()

    members = []
    for i in range(member_count):
        u = User(telegram_id=9101 + i, full_name=f"A'zo {i}")
        session.add(u)
        await session.flush()
        m = Member(user_id=u.id, group_id=group.id, role=MemberRole.MEMBER)
        session.add(m)
        await session.flush()
        members.append(m)

    task = Task(group_id=group.id, name="Vazifa", created_by_user_id=owner.id)
    session.add(task)
    await session.flush()

    doer = members[0]
    now = datetime.now(timezone.utc)
    assignment = TaskAssignment(
        task_id=task.id, member_id=doer.id, assigned_date=now, due_date=now
    )
    session.add(assignment)
    await session.flush()

    completion = TaskCompletion(
        assignment_id=assignment.id,
        member_id=doer.id,
        approval_status=CompletionApprovalStatus.PENDING,
    )
    session.add(completion)
    await session.flush()

    return members, completion


async def test_record_vote_resolves_once_majority_reached(session):
    members, completion = await _setup_group_with_completion(session, member_count=3)
    doer, voter_a, voter_b = members
    service = VotingService(CompletionVoteRepository(session))

    tally = await service.record_vote(completion.id, voter_a.id, True, eligible_total=2)
    assert tally["resolution"] is None
    assert tally["yes"] == 1
    assert tally["needed"] == 2

    tally = await service.record_vote(completion.id, voter_b.id, True, eligible_total=2)
    assert tally["resolution"] == "approved"
    assert tally["yes"] == 2


async def test_record_vote_allows_changing_mind(session):
    members, completion = await _setup_group_with_completion(session, member_count=2)
    _doer, voter = members
    service = VotingService(CompletionVoteRepository(session))

    await service.record_vote(completion.id, voter.id, True, eligible_total=1)
    tally = await service.record_vote(completion.id, voter.id, False, eligible_total=1)

    assert tally["yes"] == 0
    assert tally["no"] == 1
    assert tally["resolution"] == "rejected"
