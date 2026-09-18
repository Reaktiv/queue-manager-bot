"""
`AssignmentRepository`ning jarima o'rniga qo'shilgan/ko'chirilgan
metodlari uchun testlar:
- `get_completion_stats` / `count_all_completions` - avval
  `PenaltyRepository`da bo'lgan, jarimaga aloqasi yo'q sof statistika
  (`PenaltyRepository` o'zi jarima tizimi bilan birga olib tashlandi).
- `has_open_overdue_streak` - jarima o'rniga qo'shilgan yangi signal:
  a'zo shu vazifani oxirgi marta bajarganidan beri kamida bir kun
  kechiktirganmi (`scheduler/jobs.py` buni "eslatmani soatiga bir marta
  tezlashtirish kerakmi" degan qarorga ishlatadi).
"""

from datetime import datetime, timedelta, timezone

import pytest

from backend.src.infrastructure.models.group import Group, Member, MemberRole
from backend.src.infrastructure.models.task import Task, TaskAssignment, TaskStatus
from backend.src.infrastructure.models.user import User
from backend.src.repositories.assignment_repository import AssignmentRepository

pytestmark = pytest.mark.asyncio


async def _setup_member(session):
    owner = User(telegram_id=3100, full_name="Owner")
    session.add(owner)
    await session.flush()

    group = Group(name="Stats Group", invite_code="STATSTEST", created_by_user_id=owner.id)
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


async def test_get_completion_stats_calculates_completion_rate(session):
    member, task = await _setup_member(session)
    await _add_assignment(session, task, member, TaskStatus.PENDING, days_ago=0)
    repo = AssignmentRepository(session)

    stats = await repo.get_completion_stats(member.id)

    assert stats["total"] == 1
    assert stats["completed"] == 0
    assert stats["completion_rate"] == 0.0


async def test_get_completion_stats_with_no_assignments(session):
    member, _task = await _setup_member(session)
    repo = AssignmentRepository(session)

    stats = await repo.get_completion_stats(member.id)

    assert stats == {"total": 0, "completed": 0, "completion_rate": 0.0}


async def test_has_open_overdue_streak_false_with_no_history(session):
    member, task = await _setup_member(session)
    repo = AssignmentRepository(session)

    assert await repo.has_open_overdue_streak(task.id, member.id) is False


async def test_has_open_overdue_streak_true_after_missed_day(session):
    member, task = await _setup_member(session)
    await _add_assignment(session, task, member, TaskStatus.OVERDUE, days_ago=1)
    repo = AssignmentRepository(session)

    assert await repo.has_open_overdue_streak(task.id, member.id) is True


async def test_has_open_overdue_streak_false_once_completed_again(session):
    """A'zo bir marta o'tkazib yuborgan, keyin bajargan - streak yopiladi."""
    member, task = await _setup_member(session)
    await _add_assignment(session, task, member, TaskStatus.OVERDUE, days_ago=2)
    await _add_assignment(session, task, member, TaskStatus.COMPLETED, days_ago=1)
    repo = AssignmentRepository(session)

    assert await repo.has_open_overdue_streak(task.id, member.id) is False


async def test_has_open_overdue_streak_scoped_to_task_and_member(session):
    """Boshqa vazifadagi (yoki boshqa a'zoning) OVERDUE yozuvi ta'sir qilmasligi kerak."""
    member, task = await _setup_member(session)
    other_task = Task(group_id=task.group_id, name="Other Task", created_by_user_id=member.user_id)
    session.add(other_task)
    await session.flush()
    await _add_assignment(session, other_task, member, TaskStatus.OVERDUE, days_ago=1)
    repo = AssignmentRepository(session)

    assert await repo.has_open_overdue_streak(task.id, member.id) is False


async def test_count_all_completions(session):
    member, task = await _setup_member(session)
    assignment = await _add_assignment(session, task, member, TaskStatus.COMPLETED, days_ago=0)
    repo = AssignmentRepository(session)
    await repo.add_completion_record(
        assignment_id=assignment.id, member_id=member.id, photo_path=None, caption=None
    )

    assert await repo.count_all_completions() == 1
