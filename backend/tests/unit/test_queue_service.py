"""
QueueService uchun unit testlar - eng muhim biznes qoida: Queue Lock.
"""

import pytest

from backend.src.infrastructure.models.group import Group, Member, MemberRole
from backend.src.infrastructure.models.task import Task, TaskQueueEntry
from backend.src.infrastructure.models.user import User
from backend.src.repositories.queue_repository import QueueRepository
from backend.src.services.queue_service import QueueService

pytestmark = pytest.mark.asyncio


async def _create_task_with_queue(session, member_count: int = 3) -> tuple[Task, list[int]]:
    """Yordamchi: N ta a'zoli guruh + vazifa + navbat yaratadi."""
    owner = User(telegram_id=1000, full_name="Owner")
    session.add(owner)
    await session.flush()

    group = Group(name="Test Group", invite_code="TESTCODE", created_by_user_id=owner.id)
    session.add(group)
    await session.flush()

    member_ids = []
    for i in range(member_count):
        user = User(telegram_id=1000 + i + 1, full_name=f"Member{i}")
        session.add(user)
        await session.flush()
        member = Member(user_id=user.id, group_id=group.id, role=MemberRole.MEMBER)
        session.add(member)
        await session.flush()
        member_ids.append(member.id)

    task = Task(group_id=group.id, name="Test Task", created_by_user_id=owner.id)
    session.add(task)
    await session.flush()

    entries = [
        TaskQueueEntry(task_id=task.id, member_id=mid, position=pos)
        for pos, mid in enumerate(member_ids)
    ]
    session.add_all(entries)
    await session.flush()

    return task, member_ids


async def test_lock_current_turn_locks_only_front_entry(session):
    task, member_ids = await _create_task_with_queue(session)
    queue_repo = QueueRepository(session)
    service = QueueService(queue_repo)

    await service.lock_current_turn(task.id)

    entries = await queue_repo.get_queue_for_task(task.id)
    locked = [e for e in entries if e.is_locked]
    assert len(locked) == 1
    assert locked[0].member_id == member_ids[0]


async def test_complete_and_advance_rotates_queue_and_transfers_lock(session):
    task, member_ids = await _create_task_with_queue(session)
    queue_repo = QueueRepository(session)
    service = QueueService(queue_repo)

    await service.lock_current_turn(task.id)
    await service.complete_and_advance(task.id)

    entries = await queue_repo.get_queue_for_task(task.id)
    by_position = {e.position: e for e in entries}

    # Birinchi a'zo endi navbatning oxirida bo'lishi kerak
    assert by_position[len(member_ids) - 1].member_id == member_ids[0]
    # Ikkinchi a'zo endi boshda va QULFLANGAN bo'lishi kerak
    assert by_position[0].member_id == member_ids[1]
    assert by_position[0].is_locked is True

    # Faqat BITTA yozuv qulflangan bo'lishi shart (avvalgi bug: ikkalasi ham qolib ketardi)
    locked_entries = [e for e in entries if e.is_locked]
    assert len(locked_entries) == 1


async def test_admin_skip_unlocks_old_and_locks_new_front(session):
    task, member_ids = await _create_task_with_queue(session)
    queue_repo = QueueRepository(session)
    service = QueueService(queue_repo)

    await service.lock_current_turn(task.id)
    await service.admin_skip(task.id)

    entries = await queue_repo.get_queue_for_task(task.id)
    locked_entries = [e for e in entries if e.is_locked]

    # Regression test: admin_skip avval eski qulfni ochmagan edi
    assert len(locked_entries) == 1
    assert locked_entries[0].member_id == member_ids[1]


async def test_admin_swap_exchanges_positions(session):
    task, member_ids = await _create_task_with_queue(session)
    queue_repo = QueueRepository(session)
    service = QueueService(queue_repo)

    entries = await queue_repo.get_queue_for_task(task.id)
    entry_a, entry_b = entries[0], entries[2]

    await service.admin_swap(task.id, entry_a.member_id, entry_b.member_id)

    updated_entries = await queue_repo.get_queue_for_task(task.id)
    by_id = {e.id: e for e in updated_entries}
    assert by_id[entry_a.id].position == 2
    assert by_id[entry_b.id].position == 0


async def test_preview_queue_returns_first_three(session):
    task, member_ids = await _create_task_with_queue(session, member_count=5)
    queue_repo = QueueRepository(session)
    service = QueueService(queue_repo)

    preview = await service.preview_queue(task.id)

    assert len(preview) == 3
    assert [e.member_id for e in preview] == member_ids[:3]


async def test_get_full_queue_returns_all_members_in_order(session):
    task, member_ids = await _create_task_with_queue(session, member_count=5)
    queue_repo = QueueRepository(session)
    service = QueueService(queue_repo)

    full = await service.get_full_queue(task.id)

    assert [e.member_id for e in full] == member_ids


async def test_admin_reorder_applies_full_new_order(session):
    task, member_ids = await _create_task_with_queue(session, member_count=5)
    queue_repo = QueueRepository(session)
    service = QueueService(queue_repo)

    new_order = list(reversed(member_ids))
    await service.admin_reorder(task.id, new_order)

    updated = await queue_repo.get_queue_for_task(task.id)
    assert [e.member_id for e in updated] == new_order


async def test_admin_reorder_rejects_mismatched_member_set(session):
    task, member_ids = await _create_task_with_queue(session, member_count=3)
    queue_repo = QueueRepository(session)
    service = QueueService(queue_repo)

    # Bitta a'zo tushib qolgan (to'liq to'plam emas) - saqlanmasligi kerak.
    incomplete_order = member_ids[:2]

    with pytest.raises(ValueError):
        await service.admin_reorder(task.id, incomplete_order)

    # Hech narsa o'zgarmagan bo'lishi kerak.
    unchanged = await queue_repo.get_queue_for_task(task.id)
    assert [e.member_id for e in unchanged] == member_ids
