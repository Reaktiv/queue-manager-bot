"""
TaskService - vacation-skip (dam olishdagi a'zolarni avtomatik
o'tkazib yuborish) mantig'i uchun testlar.
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import text

from backend.src.infrastructure.models.group import Group, Member, MemberRole
from backend.src.infrastructure.models.user import User
from backend.src.repositories.audit_repository import AuditRepository
from backend.src.repositories.assignment_repository import AssignmentRepository
from backend.src.repositories.group_repository import GroupRepository
from backend.src.repositories.queue_repository import QueueRepository
from backend.src.repositories.task_repository import TaskRepository
from backend.src.repositories.user_repository import UserRepository
from backend.src.services.task_service import TaskService

pytestmark = pytest.mark.asyncio


async def _setup_group_with_members(session, vacation_flags: list[bool]):
    owner = User(telegram_id=2000, full_name="Owner")
    session.add(owner)
    await session.flush()

    group = Group(name="Vacation Test Group", invite_code="VACTEST", created_by_user_id=owner.id)
    session.add(group)
    await session.flush()

    member_ids = []
    for i, is_on_vacation in enumerate(vacation_flags):
        user = User(telegram_id=2000 + i + 1, full_name=f"M{i}")
        session.add(user)
        await session.flush()
        member = Member(
            user_id=user.id,
            group_id=group.id,
            role=MemberRole.MEMBER,
            is_on_vacation=is_on_vacation,
        )
        session.add(member)
        await session.flush()
        member_ids.append(member.id)

    return owner, group, member_ids


class FakeNotificationService:
    def __init__(self):
        self.messages: list[tuple[str, int, str]] = []

    async def build_message(self, group_id: int, template_type: str, language: str = "uz", **placeholders):
        return f"{template_type}:{placeholders['user']}:{placeholders['task']}:{placeholders['group']}"

    async def send_private_message(self, telegram_id: int, text: str) -> bool:
        self.messages.append(("private", telegram_id, text))
        return True

    async def send_group_message(self, telegram_chat_id: int, text: str) -> bool:
        self.messages.append(("group", telegram_chat_id, text))
        return True


def _make_task_service(session, notification_service=None) -> TaskService:
    return TaskService(
        task_repository=TaskRepository(session),
        queue_repository=QueueRepository(session),
        group_repository=GroupRepository(session),
        audit_repository=AuditRepository(session),
        assignment_repository=AssignmentRepository(session),
        user_repository=UserRepository(session),
        notification_service=notification_service,
    )


async def test_create_task_skips_vacationing_members_at_front(session):
    """
    3 a'zo bor: [vacation, faol, faol]. Vazifa yaratilganda navbat
    boshida darhol FAOL a'zo turishi kerak, vacation'dagi emas.
    """
    owner, group, member_ids = await _setup_group_with_members(session, [True, False, False])
    task_service = _make_task_service(session)

    task = await task_service.create_task_with_queue(
        group_id=group.id,
        name="Task",
        created_by_user_id=owner.id,
        member_ids=member_ids,
    )

    preview = await task_service.get_queue_preview(task.id)
    assert preview[0].member_id == member_ids[1]  # vacation'dagi (0) emas, faol (1) boshda


async def test_complete_task_skips_vacationing_member_after_rotation(session):
    """
    3 a'zo: [faol(A), vacation(B), faol(C)]. A bajarganda, navbat B ga
    o'tishi kerak edi, lekin B dam olishda - shuning uchun to'g'ridan-to'g'ri C ga o'tadi.
    """
    owner, group, member_ids = await _setup_group_with_members(session, [False, True, False])
    task_service = _make_task_service(session)

    task = await task_service.create_task_with_queue(
        group_id=group.id,
        name="Task",
        created_by_user_id=owner.id,
        member_ids=member_ids,
    )

    preview_before = await task_service.get_queue_preview(task.id)
    assert preview_before[0].member_id == member_ids[0]  # A boshda

    await task_service.complete_task(task.id, member_ids[0])

    preview_after = await task_service.get_queue_preview(task.id)
    assert preview_after[0].member_id == member_ids[2]  # B (vacation) chetlab o'tildi, C boshda

    entries = await QueueRepository(session).get_queue_for_task(task.id)
    locked = [e for e in entries if e.is_locked]
    assert len(locked) == 1
    assert locked[0].member_id == member_ids[2]


async def test_all_members_on_vacation_does_not_crash(session):
    """Hamma a'zo dam olishda bo'lsa, sikl cheksiz aylanmasligi kerak."""
    owner, group, member_ids = await _setup_group_with_members(session, [True, True])
    task_service = _make_task_service(session)

    task = await task_service.create_task_with_queue(
        group_id=group.id,
        name="Task",
        created_by_user_id=owner.id,
        member_ids=member_ids,
    )

    preview = await task_service.get_queue_preview(task.id)
    assert len(preview) == 2


async def test_set_vacation_skips_current_assignee(session):
    """
    3 a'zo: [faol(A), faol(B), faol(C)]. A hozir navbat boshida.
    Admin A ni dam olishga chiqarganda (set_vacation), A avtomatik ravishda
    navbat boshidan skip qilinishi va B navbat boshiga o'tishi kerak.
    """
    from backend.src.services.group_service import GroupService
    
    owner, group, member_ids = await _setup_group_with_members(session, [False, False, False])
    task_service = _make_task_service(session)
    
    group_repo = GroupRepository(session)
    group_service = GroupService(
        group_repository=group_repo,
        task_repository=TaskRepository(session),
        queue_repository=QueueRepository(session),
    )

    task = await task_service.create_task_with_queue(
        group_id=group.id,
        name="Task",
        created_by_user_id=owner.id,
        member_ids=member_ids,
    )

    preview_before = await task_service.get_queue_preview(task.id)
    assert preview_before[0].member_id == member_ids[0]  # A boshda

    # A ni dam olishga chiqaramiz
    await group_service.set_vacation(member_ids[0], is_on_vacation=True)

    preview_after = await task_service.get_queue_preview(task.id)
    assert preview_after[0].member_id == member_ids[1]  # A chetlab o'tildi, B boshda


async def test_create_task_sets_first_reminder_to_now_for_today_task(session, monkeypatch):
    owner, group, member_ids = await _setup_group_with_members(session, [False, False])
    task_service = _make_task_service(session)
    frozen_now = datetime(2026, 7, 17, 17, 30, tzinfo=timezone.utc)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return frozen_now.replace(tzinfo=None)
            return frozen_now.astimezone(tz)

    monkeypatch.setattr("backend.src.services.task_service.datetime", FrozenDateTime)

    task = await task_service.create_task_with_queue(
        group_id=group.id,
        name="Task",
        created_by_user_id=owner.id,
        member_ids=member_ids,
    )

    assert task.next_reminder_at == frozen_now


async def test_create_task_keeps_future_task_reminder_in_window(session, monkeypatch):
    owner, group, member_ids = await _setup_group_with_members(session, [False, False])
    task_service = _make_task_service(session)
    frozen_now = datetime(2026, 7, 17, 17, 30, tzinfo=timezone.utc)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return frozen_now.replace(tzinfo=None)
            return frozen_now.astimezone(tz)

    monkeypatch.setattr("backend.src.services.task_service.datetime", FrozenDateTime)

    task = await task_service.create_task_with_queue(
        group_id=group.id,
        name="Future Task",
        created_by_user_id=owner.id,
        member_ids=member_ids,
        start_date=datetime(2026, 7, 19, 0, 0, tzinfo=timezone.utc).date(),
    )

    assert task.next_reminder_at == datetime(2026, 7, 18, 3, 0, tzinfo=timezone.utc)


async def test_create_task_assigns_current_active_member_and_sends_immediate_reminders(session, monkeypatch):
    owner, group, member_ids = await _setup_group_with_members(session, [True, False, False])
    group.telegram_chat_id = -1001234567890
    notifier = FakeNotificationService()
    task_service = _make_task_service(session, notification_service=notifier)
    frozen_now = datetime(2026, 7, 19, 5, 30, tzinfo=timezone.utc)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return frozen_now.replace(tzinfo=None)
            return frozen_now.astimezone(tz)

    monkeypatch.setattr("backend.src.services.task_service.datetime", FrozenDateTime)

    task = await task_service.create_task_with_queue(
        group_id=group.id,
        name="Task",
        created_by_user_id=owner.id,
        member_ids=member_ids,
    )

    assignment_repo = task_service._assignment_repo
    assignment = await assignment_repo.get_or_create_for_local_date(
        task.id,
        member_ids[1],
        datetime(2026, 7, 19, tzinfo=timezone.utc).date(),
        group.timezone,
    )
    assert assignment.member_id == member_ids[1]
    assert notifier.messages == [
        ("private", 2002, "reminder:M1:Task:Vacation Test Group"),
        ("group", -1001234567890, 'reminder:<a href="tg://user?id=2002">M1</a>:Task:Vacation Test Group'),
    ]
    assert task.next_reminder_at == datetime(2026, 7, 19, 6, 30, tzinfo=timezone.utc)


async def test_db_session_timezone_is_asia_tashkent(session):
    result = await session.execute(text("select current_setting('TIMEZONE')"))
    assert result.scalar_one() == "Asia/Tashkent"


async def test_admin_skip_does_not_crash_when_assignment_has_penalty(session):
    """
    Regression: agar joriy (PENDING/IN_PROGRESS/OVERDUE) assignment uchun
    allaqachon Penalty yozuvi mavjud bo'lsa, admin_skip uni o'chirishga
    urinib IntegrityError (FK violation) bermasligi kerak - shu qatorni
    o'chirmasdan chetlab o'tishi kerak.
    """
    from backend.src.infrastructure.models.task import Penalty, TaskStatus
    from backend.src.utils.datetime_utils import get_local_today

    owner, group, member_ids = await _setup_group_with_members(session, [False, False])
    task_service = _make_task_service(session)

    task = await task_service.create_task_with_queue(
        group_id=group.id,
        name="Task",
        created_by_user_id=owner.id,
        member_ids=member_ids,
    )

    # create_task_with_queue allaqachon bugungi kun uchun front a'zoga (member_ids[0])
    # assignment yaratib qo'ygan (unique constraint tufayli qayta yaratib bo'lmaydi) -
    # o'shani olib, "muddati o'tgan va jarimalangan" holatga keltiramiz.
    today = get_local_today(group.timezone)
    assignment_repo = AssignmentRepository(session)
    assignment = await assignment_repo.get_or_create_for_local_date(
        task.id, member_ids[0], today, group.timezone
    )
    assignment.status = TaskStatus.OVERDUE
    await session.flush()

    penalty = Penalty(member_id=member_ids[0], task_id=task.id, assignment_id=assignment.id)
    session.add(penalty)
    await session.flush()

    # Bu chaqiruv avval "penalties_assignment_id_fkey" IntegrityError bilan qulardi.
    await task_service.admin_skip(task.id, owner.id)

    reloaded = await AssignmentRepository(session).get_by_id(assignment.id)
    assert reloaded is not None
    assert reloaded.status == TaskStatus.OVERDUE
