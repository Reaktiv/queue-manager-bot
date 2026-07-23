"""
PenaltyService uchun testlar - jarima hisoblash va 2-kunlik ogohlantirish qoidasi.

MUHIM: `should_warn` endi "ketma-ket" (consecutive) o'tkazib yuborilgan
kunlarga asoslanadi, "umr davomida jami" emas. Shuning uchun har bir
"o'tkazib yuborilgan kun" alohida TaskAssignment (status=OVERDUE) sifatida
modellashtiriladi - real ishlab chiqarish oqimida ham `check_overdue_tasks`
har bir assignment'ni `mark_overdue` qilib, keyin `register_missed_day`ni
chaqiradi (bitta assignment uchun ikki marta emas).
"""

from datetime import datetime, timedelta, timezone

import pytest

from backend.src.infrastructure.models.group import Group, Member, MemberRole
from backend.src.infrastructure.models.task import Task, TaskAssignment, TaskStatus
from backend.src.infrastructure.models.user import User
from backend.src.repositories.penalty_repository import PenaltyRepository
from backend.src.services.penalty_service import PenaltyService

pytestmark = pytest.mark.asyncio


async def _setup_member(session):
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

    return member, task


async def _add_assignment(session, task, member, status: TaskStatus, days_ago: int) -> TaskAssignment:
    assigned_date = datetime.now(timezone.utc) - timedelta(days=days_ago)
    assignment = TaskAssignment(
        task_id=task.id,
        member_id=member.id,
        assigned_date=assigned_date,
        due_date=assigned_date,
        status=status,
    )
    session.add(assignment)
    await session.flush()
    return assignment


async def test_first_missed_day_does_not_warn(session):
    member, task = await _setup_member(session)
    assignment = await _add_assignment(session, task, member, TaskStatus.OVERDUE, days_ago=0)
    service = PenaltyService(PenaltyRepository(session))

    should_warn = await service.register_missed_day(member.id, task.id, assignment.id)

    assert should_warn is False


async def test_second_consecutive_missed_day_triggers_warning(session):
    member, task = await _setup_member(session)
    await _add_assignment(session, task, member, TaskStatus.OVERDUE, days_ago=1)
    assignment_today = await _add_assignment(session, task, member, TaskStatus.OVERDUE, days_ago=0)
    service = PenaltyService(PenaltyRepository(session))

    should_warn = await service.register_missed_day(member.id, task.id, assignment_today.id)

    assert should_warn is True


async def test_non_consecutive_missed_days_do_not_warn(session):
    """
    A'zo bir marta o'tkazib yuborgan, keyin vaqtida bajargan, so'ng яна bir
    marta o'tkazib yuborgan bo'lsa - bu "2 kun ketma-ket" emas, shuning
    uchun ogohlantirish yuborilmasligi kerak.
    """
    member, task = await _setup_member(session)
    await _add_assignment(session, task, member, TaskStatus.OVERDUE, days_ago=2)
    await _add_assignment(session, task, member, TaskStatus.COMPLETED, days_ago=1)
    assignment_today = await _add_assignment(session, task, member, TaskStatus.OVERDUE, days_ago=0)
    service = PenaltyService(PenaltyRepository(session))

    should_warn = await service.register_missed_day(member.id, task.id, assignment_today.id)

    assert should_warn is False


async def test_get_member_statistics_calculates_completion_rate(session):
    member, task = await _setup_member(session)
    await _add_assignment(session, task, member, TaskStatus.PENDING, days_ago=0)
    service = PenaltyService(PenaltyRepository(session))

    stats = await service.get_member_statistics(member.id)

    assert stats["total"] == 1
    assert stats["completed"] == 0
    assert stats["completion_rate"] == 0.0
    assert stats["current_penalty"] == 0
