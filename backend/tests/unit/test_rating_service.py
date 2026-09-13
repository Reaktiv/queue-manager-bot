"""
RatingService uchun testlar - 5 yulduzli profil darajasi (aralash model).

Formula: daraja = clamp(guruhdoshlar bergan o'rtacha ball (hali baho
bo'lmasa 5.0 dan boshlanadi) - jami jarima balli, 1.0, 5.0)
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from backend.src.infrastructure.models.group import Group, Member, MemberRole
from backend.src.infrastructure.models.task import (
    CompletionApprovalStatus,
    Task,
    TaskAssignment,
    TaskCompletion,
)
from backend.src.infrastructure.models.user import User
from backend.src.repositories.completion_rating_repository import CompletionRatingRepository
from backend.src.repositories.group_repository import GroupRepository
from backend.src.repositories.penalty_repository import PenaltyRepository
from backend.src.services.rating_service import RatingService

pytestmark = pytest.mark.asyncio


async def _setup_group_with_members(session, member_count: int = 2):
    owner = User(telegram_id=9000, full_name="Owner")
    session.add(owner)
    await session.flush()

    group = Group(name="Rating Group", invite_code="RATETEST", created_by_user_id=owner.id)
    session.add(group)
    await session.flush()

    members = []
    for i in range(member_count):
        u = User(telegram_id=9001 + i, full_name=f"A'zo {i}")
        session.add(u)
        await session.flush()
        m = Member(user_id=u.id, group_id=group.id, role=MemberRole.MEMBER)
        session.add(m)
        await session.flush()
        members.append(m)

    task = Task(group_id=group.id, name="Vazifa", created_by_user_id=owner.id)
    session.add(task)
    await session.flush()

    return group, members, task


async def _add_approved_completion(session, task, member) -> TaskCompletion:
    now = datetime.now(timezone.utc)
    assignment = TaskAssignment(
        task_id=task.id, member_id=member.id, assigned_date=now, due_date=now
    )
    session.add(assignment)
    await session.flush()

    completion = TaskCompletion(
        assignment_id=assignment.id,
        member_id=member.id,
        approval_status=CompletionApprovalStatus.APPROVED,
    )
    session.add(completion)
    await session.flush()
    return completion


def _service(session) -> RatingService:
    return RatingService(
        rating_repository=CompletionRatingRepository(session),
        penalty_repository=PenaltyRepository(session),
        group_repository=GroupRepository(session),
    )


async def test_new_member_starts_at_five_stars(session):
    _group, members, _task = await _setup_group_with_members(session, member_count=1)
    service = _service(session)

    stars = await service.recalculate_and_get(members[0].id)

    assert stars == Decimal("5.00")


async def test_peer_rating_average_becomes_the_base(session):
    group, members, task = await _setup_group_with_members(session, member_count=2)
    rated, rater = members
    completion = await _add_approved_completion(session, task, rated)
    service = _service(session)

    await service._rating_repo.upsert_rating(completion.id, rater.id, stars=3)
    result = await service.recalculate_and_get(rated.id)

    assert result == Decimal("3.00")


async def test_missed_deadline_subtracts_one_star(session):
    group, members, task = await _setup_group_with_members(session, member_count=1)
    member = members[0]
    now = datetime.now(timezone.utc)
    assignment = TaskAssignment(
        task_id=task.id, member_id=member.id, assigned_date=now, due_date=now
    )
    session.add(assignment)
    await session.flush()
    await PenaltyRepository(session).add_penalty(member.id, task.id, assignment.id)

    service = _service(session)
    stars = await service.recalculate_and_get(member.id)

    # 5.0 (baza, hali baho yo'q) - 1 (bitta jarima) = 4.0
    assert stars == Decimal("4.00")


async def test_rating_never_drops_below_one_star(session):
    group, members, task = await _setup_group_with_members(session, member_count=1)
    member = members[0]
    penalty_repo = PenaltyRepository(session)
    now = datetime.now(timezone.utc)
    for day in range(10):
        # Har bir assignment BOSHQA kunga tegishli bo'lishi kerak -
        # (task_id, member_id, assigned_date) unique cheklovi bor.
        assigned_date = now - timedelta(days=day)
        assignment = TaskAssignment(
            task_id=task.id, member_id=member.id, assigned_date=assigned_date, due_date=assigned_date
        )
        session.add(assignment)
        await session.flush()
        await penalty_repo.add_penalty(member.id, task.id, assignment.id)

    service = _service(session)
    stars = await service.recalculate_and_get(member.id)

    # 5.0 - 10 jarima = -5.0, lekin 1.0 dan pastga tushmasligi kerak.
    assert stars == Decimal("1.00")


async def test_peer_rating_and_penalty_combine(session):
    group, members, task = await _setup_group_with_members(session, member_count=2)
    rated, rater = members
    completion = await _add_approved_completion(session, task, rated)

    penalty_repo = PenaltyRepository(session)
    now = datetime.now(timezone.utc)
    assignment = TaskAssignment(
        task_id=task.id, member_id=rated.id, assigned_date=now, due_date=now
    )
    session.add(assignment)
    await session.flush()
    await penalty_repo.add_penalty(rated.id, task.id, assignment.id)

    service = _service(session)
    await service._rating_repo.upsert_rating(completion.id, rater.id, stars=4)
    stars = await service.recalculate_and_get(rated.id)

    # 4.0 (guruhdosh bahosi) - 1 (jarima) = 3.0
    assert stars == Decimal("3.00")


async def test_get_profile_rating_returns_breakdown(session):
    group, members, task = await _setup_group_with_members(session, member_count=2)
    rated, rater = members
    completion = await _add_approved_completion(session, task, rated)
    service = _service(session)
    await service._rating_repo.upsert_rating(completion.id, rater.id, stars=5)

    profile = await service.get_profile_rating(rated.id)

    assert profile["rating_stars"] == 5.0
    assert profile["peer_rating_avg"] == 5.0
    assert profile["rating_count"] == 1
    assert profile["penalty_points"] == 0
