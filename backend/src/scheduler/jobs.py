"""
Scheduler vazifalari (background jobs).

Bu modul APScheduler tomonidan davriy chaqiriladi. Har bir funksiya
o'zining DB sessiyasini ochadi va yopadi (background job'lar request-scoped
dependency injection'dan foydalana olmaydi).
"""

from datetime import datetime, timezone

import structlog

from ..infrastructure.db.session import async_session_factory
from ..infrastructure.models.group import Group
from ..repositories.assignment_repository import AssignmentRepository
from ..repositories.completion_vote_repository import CompletionVoteRepository
from ..repositories.group_repository import GroupRepository
from ..repositories.notification_repository import NotificationTemplateRepository
from ..repositories.queue_repository import QueueRepository
from ..repositories.task_repository import TaskRepository
from ..repositories.audit_repository import AuditRepository
from ..repositories.user_repository import UserRepository
from ..services.notification_service import NotificationService, format_telegram_html_mention
from ..services.photo_completion_service import CompletionService
from ..services.photo_storage_service import PhotoStorageService
from ..services.task_service import TaskService
from ..services.voting_service import VotingService
from ..utils.datetime_utils import (
    calculate_next_reminder_at,
    get_timezone,
    get_local_today,
    local_date_to_utc_start,
    reminder_window_start_utc,
    utc_to_local_date,
)
from sqlalchemy import select

logger = structlog.get_logger()


async def _send_reminder_for_task(
    session,
    group,
    task,
    now,
    task_repo,
    queue_repo,
    group_repo,
    user_repo,
    notification_service,
    assignment_repo,
) -> None:
    from ..infrastructure.models.task import TaskAssignment, TaskStatus

    if task.next_reminder_at is None or now < task.next_reminder_at:
        return

    # IN_PROGRESS holati - a'zo rasmni allaqachon yuborgan, guruh tasdiqlashini
    # kutmoqda. Bunday holatda "hali bajarmadingiz" eslatmasi noto'g'ri bo'lardi.
    assignment_stmt = (
        select(TaskAssignment)
        .where(
            TaskAssignment.task_id == task.id,
            TaskAssignment.status.in_([TaskStatus.PENDING, TaskStatus.OVERDUE]),
        )
        .order_by(TaskAssignment.assigned_date.desc())
        .limit(1)
    )
    assignment_result = await session.execute(assignment_stmt)
    pending_assignment = assignment_result.scalar_one_or_none()
    if pending_assignment is None:
        return

    current_entry = await queue_repo.get_current_entry(task.id)
    if current_entry is None or current_entry.member_id != pending_assignment.member_id:
        return

    member = await group_repo.get_member_by_id(current_entry.member_id)
    if member is None or member.is_on_vacation:
        return

    user = await user_repo.get_by_id(member.user_id)
    if user is None:
        return

    text = await notification_service.build_message(
        group_id=group.id,
        template_type="reminder",
        language=user.language,
        user=user.full_name,
        task=task.name,
        group=group.name,
    )

    # Shaxsiy eslatmaga "✅ Bajarish" tugmasi qo'shiladi - foydalanuvchi
    # /mytasks'ga qaytmasdan, to'g'ridan-to'g'ri shu xabardan bosib rasm
    # yuklash oqimini boshlay oladi. Callback formati botning
    # `complete:{task_id}` handleri (my_tasks.py) bilan bir xil - qaysi
    # jarayon xabarni yuborganidan qat'i nazar, tugma bosilganda kelgan
    # callback bot yangilanishlar oqimidan odatdagidek ishlanadi.
    complete_keyboard = {
        "inline_keyboard": [[{"text": "✅ Bajarish", "callback_data": f"complete:{task.id}"}]]
    }
    await notification_service.send_private_message(
        user.telegram_id, text, reply_markup=complete_keyboard
    )
    logger.info("reminder_sent_private", task_id=task.id, user_telegram_id=user.telegram_id)

    if group.telegram_chat_id:
        group_text = await notification_service.build_message(
            group_id=group.id,
            template_type="reminder",
            language=user.language,
            user=format_telegram_html_mention(user.full_name, user.telegram_id),
            task=task.name,
            group=group.name,
        )
        await notification_service.send_group_message(group.telegram_chat_id, group_text)
        logger.info("reminder_sent_group", task_id=task.id, telegram_chat_id=group.telegram_chat_id)

    # Muddati o'tib, kamida bir kun kechikkan bo'lsa (jarima o'rniga) eslatma
    # tezlashtiriladi - vazifaning o'zi sozlagan oralig'idan qat'i nazar,
    # har 1 soatda (hamon sozlangan eslatma oynasi ichida) qayta-qayta
    # eslatib turiladi, toki bajarilmaguncha.
    overdue_streak = await assignment_repo.has_open_overdue_streak(
        task.id, current_entry.member_id
    )
    interval_min = 60 if overdue_streak else task.reminder_interval_min_minutes
    interval_max = 60 if overdue_streak else task.reminder_interval_max_minutes

    next_rem = calculate_next_reminder_at(
        now_utc=now,
        timezone_str=group.timezone if group else "Asia/Tashkent",
        interval_min_minutes=interval_min,
        interval_max_minutes=interval_max,
        start_hour=task.reminder_start_hour,
        end_hour=task.reminder_end_hour,
    )
    task.next_reminder_at = next_rem


async def send_reminders() -> None:
    """
    Har bir faol vazifa uchun: agar hozirgi vaqt next_reminder_at dan o'tgan bo'lsa
    va bugungi topshiriq hali bajarilmagan (PENDING) bo'lsa - private va group xabari yuboriladi.

    Muddati o'tib, kamida bir kun kechikkan vazifalar uchun bu eslatmalar
    avtomatik har 1 soatda takrorlanadi (`_send_reminder_for_task`) - jarima
    o'rniga tanlangan yondashuv: ball hisoblanmaydi, o'rniga tez-tez eslatiladi.

    Har bir vazifa alohida try/except bilan qayta ishlanadi - bitta vazifadagi
    kutilmagan xatolik (masalan, eskidan qolgan noto'g'ri reminder soatlari)
    boshqa barcha guruhlar uchun eslatmalar yuborilishini to'xtatib qo'ymasligi kerak.
    """
    async with async_session_factory() as session:
        task_repo = TaskRepository(session)
        queue_repo = QueueRepository(session)
        group_repo = GroupRepository(session)
        user_repo = UserRepository(session)
        assignment_repo = AssignmentRepository(session)
        template_repo = NotificationTemplateRepository(session)
        notification_service = NotificationService(template_repo)

        now = datetime.now(timezone.utc)

        groups_result = await session.execute(select(Group).where(Group.is_active.is_(True)))
        groups = list(groups_result.scalars().all())

        for group in groups:
            tasks = await task_repo.list_by_group(group.id, active_only=True)
            for task in tasks:
                try:
                    await _send_reminder_for_task(
                        session, group, task, now, task_repo, queue_repo, group_repo, user_repo,
                        notification_service, assignment_repo,
                    )
                except Exception:
                    logger.exception("send_reminders_task_failed", task_id=task.id, group_id=group.id)

        await session.commit()


async def _process_overdue_assignment(
    session, assignment, assignment_repo, task_repo, group_repo, user_repo, notification_service,
) -> None:
    await assignment_repo.mark_overdue(assignment)

    task = await task_repo.get_by_id(assignment.task_id)
    member = await group_repo.get_member_by_id(assignment.member_id)
    if task is None or member is None:
        return
    user = await user_repo.get_by_id(member.user_id)
    if user is None:
        return

    text = await notification_service.build_message(
        group_id=task.group_id,
        template_type="overdue",
        language=user.language,
        user=user.full_name,
        task=task.name,
    )
    await notification_service.send_private_message(user.telegram_id, text)

    # Jarima o'rniga: guruhga ham DARHOL (2 kun kutmasdan) xabar beriladi -
    # "har soatda eslatib turish" rejimi shu paytdan boshlab
    # `send_reminders`/`_send_reminder_for_task` orqali davom etadi.
    group = await group_repo.get_by_id(task.group_id)
    if group and group.telegram_chat_id:
        group_text = await notification_service.build_message(
            group_id=task.group_id,
            template_type="overdue",
            language=user.language,
            user=format_telegram_html_mention(user.full_name, user.telegram_id),
            task=task.name,
        )
        await notification_service.send_group_message(group.telegram_chat_id, group_text)

    logger.info(
        "task_marked_overdue", task_id=assignment.task_id, member_id=assignment.member_id
    )


async def check_overdue_tasks() -> None:
    """
    Muddati o'tgan (23:59 dan keyin hali bajarilmagan) vazifalarni topib:
    1. Assignment'ni OVERDUE qiladi.
    2. A'zoga (shaxsiy) va guruhga "muddati o'tdi" xabari yuboriladi.
    3. Navbat HECH QACHON o'chmaydi - ertaga ham shu a'zoda qoladi
       (Queue Lock saqlanadi, ya'ni hech narsa qilmaymiz - u allaqachon qulflangan).

    DIQQAT: bu yerda jarima/ball HISOBLANMAYDI (talab bo'yicha olib
    tashlangan) - o'rniga ertasi kundan boshlab `send_reminders` shu a'zoga
    (guruh + shaxsiy) har 1 soatda qayta-qayta eslatadi, toki bajarilmaguncha
    (`AssignmentRepository.has_open_overdue_streak`).

    Har bir assignment alohida try/except bilan qayta ishlanadi - bitta a'zodagi
    xatolik boshqalarga xabar yuborilishini to'xtatmasligi kerak.
    """
    async with async_session_factory() as session:
        assignment_repo = AssignmentRepository(session)
        task_repo = TaskRepository(session)
        group_repo = GroupRepository(session)
        user_repo = UserRepository(session)
        template_repo = NotificationTemplateRepository(session)
        notification_service = NotificationService(template_repo)

        now = datetime.now(timezone.utc)
        overdue_assignments = await assignment_repo.get_pending_overdue(now)

        for assignment in overdue_assignments:
            try:
                await _process_overdue_assignment(
                    session, assignment, assignment_repo,
                    task_repo, group_repo, user_repo, notification_service,
                )
            except Exception:
                logger.exception(
                    "check_overdue_tasks_assignment_failed", assignment_id=assignment.id
                )

        await session.commit()


async def _generate_assignment_for_task(
    session, group, task, local_today, queue_repo, assignment_repo,
) -> None:
    from datetime import timedelta

    if task.next_execution_date:
        if local_today < utc_to_local_date(task.next_execution_date, group.timezone):
            return

    current_entry = await queue_repo.get_current_entry(task.id)
    if current_entry is None:
        return

    await assignment_repo.get_or_create_for_local_date(
        task.id,
        current_entry.member_id,
        local_today,
        group.timezone,
    )

    interval = task.schedule_interval_days or 1
    next_local_date = local_today + timedelta(days=interval)
    task.next_execution_date = local_date_to_utc_start(next_local_date, group.timezone)

    task.next_reminder_at = reminder_window_start_utc(
        local_date=local_today,
        timezone_str=group.timezone,
        start_hour=task.reminder_start_hour,
    )


async def generate_daily_assignments() -> None:
    """
    Har kuni (masalan, 00:05 da) faol vazifalar uchun bugungi
    assignment'larni oldindan yaratib qo'yadi (agar bugun bajarish kuni bo'lsa).

    Har bir vazifa alohida try/except bilan qayta ishlanadi - bitta vazifadagi
    xatolik boshqa guruhlar/vazifalar uchun assignment yaratilishini to'xtatmasligi kerak.
    """
    async with async_session_factory() as session:
        task_repo = TaskRepository(session)
        queue_repo = QueueRepository(session)
        assignment_repo = AssignmentRepository(session)

        groups_result = await session.execute(select(Group).where(Group.is_active.is_(True)))
        groups = list(groups_result.scalars().all())

        now = datetime.now(timezone.utc)

        for group in groups:
            local_today = get_local_today(group.timezone, now)
            tasks = await task_repo.list_by_group(group.id, active_only=True)
            for task in tasks:
                try:
                    await _generate_assignment_for_task(
                        session, group, task, local_today, queue_repo, assignment_repo,
                    )
                except Exception:
                    logger.exception(
                        "generate_daily_assignments_task_failed", task_id=task.id, group_id=group.id
                    )

        await session.commit()
        logger.info("daily_assignments_generated")


async def _send_pre_warning_for_task(
    session, group, task, local_now, local_hour, tz, queue_repo, group_repo, user_repo,
    notification_service,
) -> None:
    if not task.next_execution_date:
        return

    # Difference in days
    task_local_exec = task.next_execution_date.astimezone(tz)
    days_left = (task_local_exec.date() - local_now.date()).days

    if days_left != 1:
        return

    # Check if already sent for this execution date
    if task.last_pre_warning_sent_date:
        last_sent_local = task.last_pre_warning_sent_date.astimezone(tz)
        if last_sent_local.date() == task_local_exec.date():
            return

    # Send at reminder_start_hour (or if we are past it and haven't sent it yet)
    if local_hour < task.reminder_start_hour:
        return

    current_entry = await queue_repo.get_current_entry(task.id)
    if current_entry is None:
        return

    member = await group_repo.get_member_by_id(current_entry.member_id)
    if member is None or member.is_on_vacation:
        return

    user = await user_repo.get_by_id(member.user_id)
    if user is None:
        return

    text = (
        f"🔔 <b>Eslatma (1 kun oldin):</b>\n\n"
        f"Ertaga sizning <b>{task.name}</b> vazifasida navbatingiz keladi!"
    )

    success = await notification_service.send_private_message(user.telegram_id, text)
    if success:
        task.last_pre_warning_sent_date = task.next_execution_date
        logger.info("pre_warning_sent", task_id=task.id, user_telegram_id=user.telegram_id)


async def send_pre_warnings() -> None:
    """
    Vazifaga 1 kun qolganda foydalanuvchini ogohlantirish xabari yuboriladi.
    Xabar faqat 1 marta, guruhning reminder_start_hour soatida yuboriladi.

    Har bir vazifa alohida try/except bilan qayta ishlanadi - bitta vazifadagi
    xatolik boshqa vazifalar uchun ogohlantirish yuborilishini to'xtatmasligi kerak.
    """
    async with async_session_factory() as session:
        task_repo = TaskRepository(session)
        queue_repo = QueueRepository(session)
        group_repo = GroupRepository(session)
        user_repo = UserRepository(session)
        template_repo = NotificationTemplateRepository(session)
        notification_service = NotificationService(template_repo)

        now = datetime.now(timezone.utc)

        groups_result = await session.execute(select(Group).where(Group.is_active.is_(True)))
        groups = list(groups_result.scalars().all())

        for group in groups:
            # Ilgari bu yerda qat'iy DEFAULT_ZONEINFO turardi, ya'ni guruh
            # halqasi ichida bo'lsa ham har bir guruh uchun bir xil (Toshkent)
            # soat ishlatilardi. Qolgan barcha job'lar guruh vaqt zonasini
            # hisobga oladi - bu bittasi mos kelmay qolgan edi.
            tz = get_timezone(group.timezone)
            local_now = now.astimezone(tz)
            local_hour = local_now.hour

            tasks = await task_repo.list_by_group(group.id, active_only=True)
            for task in tasks:
                try:
                    await _send_pre_warning_for_task(
                        session, group, task, local_now, local_hour, tz, queue_repo, group_repo,
                        user_repo, notification_service,
                    )
                except Exception:
                    logger.exception(
                        "send_pre_warnings_task_failed", task_id=task.id, group_id=group.id
                    )

        await session.commit()


async def resolve_expired_completion_votes() -> None:
    """
    2 soatlik ovoz berish oynasi tugagan, lekin hali PENDING qolgan
    topshiriqlarni yig'ilgan ovozlar bo'yicha yakunlaydi (agar hech kim
    ovoz bosib ulgurmagan bo'lsa - ko'pchilik yig'ilmagan holatning o'zi -
    "sukut - rozilik" bilan tasdiqlanadi). Har bir yakunlangan topshiriq
    uchun guruhga va bajaruvchiga xabar yuboriladi.

    `submit_vote` orqali ko'pchilik darhol hosil bo'lgan hollar bu yerga
    kirmaydi - ular botning o'zi (`bot/handlers/votes.py`) tomonidan
    darhol xabar qilinadi.
    """
    async with async_session_factory() as session:
        assignment_repo = AssignmentRepository(session)
        group_repo = GroupRepository(session)
        user_repo = UserRepository(session)
        audit_repo = AuditRepository(session)
        template_repo = NotificationTemplateRepository(session)
        notification_service = NotificationService(template_repo)
        task_service = TaskService(
            task_repository=TaskRepository(session),
            queue_repository=QueueRepository(session),
            group_repository=group_repo,
            audit_repository=audit_repo,
            assignment_repository=assignment_repo,
            user_repository=user_repo,
            notification_service=notification_service,
        )
        completion_service = CompletionService(
            assignment_repository=assignment_repo,
            group_repository=group_repo,
            task_service=task_service,
            photo_storage=PhotoStorageService(),
            notification_service=notification_service,
            user_repository=user_repo,
            voting_service=VotingService(CompletionVoteRepository(session)),
        )

        try:
            resolved = await completion_service.resolve_expired_votes()
        except Exception:
            logger.exception("resolve_expired_completion_votes_failed")
            return

        for item in resolved:
            assignee_name = item["assignee_name"] or "A'zo"
            if item["resolution"] == "approved":
                group_text = (
                    f"✅ <b>{item['task_name']}</b> uchun ovoz berish muddati tugadi - "
                    f"{assignee_name} bajargan deb hisoblandi ({item['yes']} ha / {item['no']} yo'q). "
                    f"Navbat keyingi a'zoga o'tdi."
                )
                dm_text = (
                    f"✅ \"{item['task_name']}\" vazifangiz ovoz berish muddati tugagach "
                    f"bajarilgan deb hisoblandi. Navbat keyingi a'zoga o'tdi."
                )
            else:
                group_text = (
                    f"❌ <b>{item['task_name']}</b> uchun ovoz berish muddati tugadi - "
                    f"{assignee_name} bajarmagan deb hisoblandi ({item['yes']} ha / {item['no']} yo'q). "
                    f"Vazifa qaytadan shu a'zoga topshirildi."
                )
                dm_text = (
                    f"❌ \"{item['task_name']}\" vazifangiz ovoz berish muddati tugagach "
                    f"bajarilmagan deb hisoblandi. Iltimos, qaytadan bajaring."
                )

            if item["telegram_chat_id"]:
                await notification_service.send_group_message(item["telegram_chat_id"], group_text)
            if item["assignee_telegram_id"]:
                await notification_service.send_private_message(
                    item["assignee_telegram_id"], dm_text
                )
            logger.info(
                "completion_vote_resolved_on_timeout",
                completion_id=item["completion_id"],
                resolution=item["resolution"],
            )

        await session.commit()
