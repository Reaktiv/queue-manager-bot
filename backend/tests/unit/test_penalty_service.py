"""
PenaltyService uchun testlar - jarima hisoblash va 2-kunlik ogohlantirish qoidasi.
"""

from datetime import datetime, timezone

import pytest

from backend.src.infrastructure.models.group import Group, Member, MemberRole
from backend.src.infrastructure.models.task import Task, TaskAssignment, TaskStatus
from backend.src.infrastructure.models.user import User
from backend.src.repositories.penalty_repository import PenaltyRepository
from backend.src.services.penalty_service import PenaltyService

pytestmark = pytest.mark.asyncio


async def _setup_member_with_assignment(session):
    owner = User(telegram_id=3000, full_name="Owner")
    session.add(owner)
    await session.flush()

    group = Group(name="Penalty Group", invite_code="PENTEST", created_by_user_id=owner.id)
    session.add(group)
    await session.flush()

    member = Member(user_id=owner.id, group_id=group.id, role=MemberRole.MEMBER)
    session.add(member)
    await session.flush()

    task = Task(group_id=group.id, name="Task", created_by_user_id=owner.id)
    session.add(task)
    await session.flush()

    assignment = TaskAssignment(
        task_id=task.id,
        member_id=member.id,
        assigned_date=datetime.now(timezone.utc),
        due_date=datetime.now(timezone.utc),
        status=TaskStatus.PENDING,
    )
    session.add(assignment)
    await session.flush()

    return member, task, assignment


async def test_first_missed_day_does_not_warn(session):
    member, task, assignment = await _setup_member_with_assignment(session)
    service = PenaltyService(PenaltyRepository(session))

    should_warn = await service.register_missed_day(member.id, task.id, assignment.id)

    assert should_warn is False


async def test_second_missed_day_triggers_warning(session):
    member, task, assignment = await _setup_member_with_assignment(session)
    service = PenaltyService(PenaltyRepository(session))

    await service.register_missed_day(member.id, task.id, assignment.id)
    should_warn = await service.register_missed_day(member.id, task.id, assignment.id)

    assert should_warn is True


async def test_get_member_statistics_calculates_completion_rate(session):
    member, task, assignment = await _setup_member_with_assignment(session)
    service = PenaltyService(PenaltyRepository(session))

    stats = await service.get_member_statistics(member.id)

    assert stats["total"] == 1
    assert stats["completed"] == 0
    assert stats["completion_rate"] == 0.0
    assert stats["current_penalty"] == 0
