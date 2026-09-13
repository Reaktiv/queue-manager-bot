"""
Presentation Layer: Task, Queue va admin amallari uchun endpointlar.
"""

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, model_validator

from ....api.deps import (
    get_group_service,
    get_queue_service,
    get_session,
    get_task_service,
    get_user_service,
)
from ....api.auth_deps import (
    Identity,
    ensure_actor_can_access_group,
    ensure_actor_owns_telegram_id,
    ensure_admin_for_group,
    verify_bot_or_mini_app,
)
from ....services.group_service import GroupService
from ....services.queue_service import QueueService
from ....services.task_service import TaskService
from ....services.user_service import UserService
from ....utils.datetime_utils import get_local_today, utc_to_local_date
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    prefix="/tasks", tags=["Tasks & Queue"], dependencies=[Depends(verify_bot_or_mini_app)]
)


class ApiResponse(BaseModel):
    success: bool
    data: object | None = None
    message: str | None = None


class QueueEntryOut(BaseModel):
    id: int
    member_id: int
    position: int
    is_locked: bool

    model_config = {"from_attributes": True}


def _build_queue_schedule_dates(task, timezone_str: str, size: int) -> list[str | None]:
    if size <= 0:
        return []

    interval_days = task.schedule_interval_days or 1
    base_local_date: date | None = None

    if task.next_execution_date:
        next_local_date = utc_to_local_date(task.next_execution_date, timezone_str)
        if task.start_date:
            start_local_date = utc_to_local_date(task.start_date, timezone_str)
            if next_local_date <= start_local_date:
                base_local_date = next_local_date
            else:
                base_local_date = next_local_date - timedelta(days=interval_days)
        else:
            base_local_date = next_local_date - timedelta(days=interval_days)
    elif task.start_date:
        base_local_date = utc_to_local_date(task.start_date, timezone_str)

    if base_local_date is None:
        return [None] * size

    return [
        (base_local_date + timedelta(days=interval_days * index)).isoformat()
        for index in range(size)
    ]


def _entries_to_data(entries, task=None, timezone_str: str = "Asia/Tashkent") -> list[dict]:
    scheduled_dates = _build_queue_schedule_dates(task, timezone_str, len(entries)) if task else [None] * len(entries)
    res = []
    for e, scheduled_date in zip(entries, scheduled_dates):
        d = QueueEntryOut.model_validate(e).model_dump()
        d["full_name"] = e.member.user.full_name if e.member and e.member.user else f"a'zo #{e.member_id}"
        d["scheduled_date"] = scheduled_date
        res.append(d)
    return res


class CreateTaskRequest(BaseModel):
    telegram_id: int
    group_id: int
    name: str
    description: str | None = None
    schedule_interval_days: int = Field(default=1, gt=0)
    reminder_interval_min_minutes: int = Field(default=60, gt=0)
    reminder_interval_max_minutes: int = Field(default=60, gt=0)
    reminder_start_hour: int = Field(default=8, ge=0, le=23)
    reminder_end_hour: int = Field(default=22, ge=0, le=23)
    require_photo: bool = True
    priority: int = 0
    start_date: str | None = None

    @model_validator(mode="after")
    def _check_reminder_window(self) -> "CreateTaskRequest":
        if self.reminder_start_hour >= self.reminder_end_hour:
            raise ValueError("reminder_start_hour reminder_end_hour'dan kichik bo'lishi kerak")
        if self.reminder_interval_min_minutes > self.reminder_interval_max_minutes:
            raise ValueError(
                "reminder_interval_min_minutes reminder_interval_max_minutes'dan katta bo'lmasligi kerak"
            )
        return self


class UpdateTaskRequest(BaseModel):
    telegram_id: int
    name: str | None = None
    description: str | None = None
    reminder_interval_min_minutes: int | None = Field(default=None, gt=0)
    reminder_interval_max_minutes: int | None = Field(default=None, gt=0)
    reminder_start_hour: int | None = Field(default=None, ge=0, le=23)
    reminder_end_hour: int | None = Field(default=None, ge=0, le=23)
    require_photo: bool | None = None
    priority: int | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def _check_reminder_window(self) -> "UpdateTaskRequest":
        if (
            self.reminder_start_hour is not None
            and self.reminder_end_hour is not None
            and self.reminder_start_hour >= self.reminder_end_hour
        ):
            raise ValueError("reminder_start_hour reminder_end_hour'dan kichik bo'lishi kerak")
        if (
            self.reminder_interval_min_minutes is not None
            and self.reminder_interval_max_minutes is not None
            and self.reminder_interval_min_minutes > self.reminder_interval_max_minutes
        ):
            raise ValueError(
                "reminder_interval_min_minutes reminder_interval_max_minutes'dan katta bo'lmasligi kerak"
            )
        return self


class AdminActionRequest(BaseModel):
    telegram_id: int


class SwapRequest(BaseModel):
    telegram_id: int
    member_id_a: int
    member_id_b: int


class ReorderRequest(BaseModel):
    telegram_id: int
    member_ids: list[int] = Field(min_length=1)


async def _resolve_user_id(user_service: UserService, telegram_id: int) -> int | None:
    user = await user_service.get_by_telegram_id(telegram_id)
    return user.id if user else None


@router.post("/", response_model=ApiResponse)
async def create_task(
    payload: CreateTaskRequest,
    session: AsyncSession = Depends(get_session),
    task_service: TaskService = Depends(get_task_service),
    user_service: UserService = Depends(get_user_service),
    group_service: GroupService = Depends(get_group_service),
    identity: Identity = Depends(verify_bot_or_mini_app),
):
    await ensure_actor_owns_telegram_id(identity, payload.telegram_id, session)
    user_id = await _resolve_user_id(user_service, payload.telegram_id)
    if user_id is None:
        return ApiResponse(success=False, message="Avval /start orqali ro'yxatdan o'ting")

    await ensure_admin_for_group(user_id, payload.group_id, session)

    group = await group_service._repo.get_by_id(payload.group_id)
    if group is None:
        return ApiResponse(success=False, message="Guruh topilmadi")

    start_date_dt = None
    if payload.start_date:
        try:
            start_date_dt = datetime.strptime(payload.start_date.strip(), "%Y-%m-%d").date()
        except ValueError:
            return ApiResponse(success=False, message="Sana formati noto'g'ri (YYYY-MM-DD bo'lishi kerak)")

    task = await task_service.create_task_with_queue(
        group_id=payload.group_id,
        name=payload.name,
        created_by_user_id=user_id,
        description=payload.description,
        schedule_interval_days=payload.schedule_interval_days,
        reminder_interval_min_minutes=payload.reminder_interval_min_minutes,
        reminder_interval_max_minutes=payload.reminder_interval_max_minutes,
        reminder_start_hour=payload.reminder_start_hour,
        reminder_end_hour=payload.reminder_end_hour,
        require_photo=payload.require_photo,
        priority=payload.priority,
        start_date=start_date_dt,
    )
    return ApiResponse(
        success=True,
        data={"task_id": task.id, "name": task.name},
        message="Vazifa yaratildi va navbat shakllantirildi",
    )


@router.get("/group/{group_id}", response_model=ApiResponse)
async def list_group_tasks(
    group_id: int,
    session: AsyncSession = Depends(get_session),
    task_service: TaskService = Depends(get_task_service),
    group_service: GroupService = Depends(get_group_service),
    identity: Identity = Depends(verify_bot_or_mini_app),
):
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from ....infrastructure.models.group import Member

    await ensure_actor_can_access_group(identity, group_id, session)

    tasks = await task_service.list_group_tasks(group_id)
    group = await group_service._repo.get_by_id(group_id)
    timezone_str = group.timezone if group else "Asia/Tashkent"
    data = []
    for t in tasks:
        current_entry = await task_service._queue_repo.get_current_entry(t.id)
        current_assignee = "Hech kim"
        if current_entry:
            stmt = (
                select(Member)
                .options(selectinload(Member.user))
                .where(Member.id == current_entry.member_id)
            )
            res_member = await session.execute(stmt)
            member = res_member.scalar_one_or_none()
            if member and member.user:
                current_assignee = member.user.full_name
        
        data.append({
            "id": t.id,
            "name": t.name,
            "priority": t.priority,
            "is_active": t.is_active,
            "current_assignee": current_assignee,
            "current_turn_date": (
                _build_queue_schedule_dates(t, timezone_str, 1)[0]
                if (t.next_execution_date or t.start_date)
                else None
            ),
            "reminder_interval_min_minutes": t.reminder_interval_min_minutes,
            "reminder_interval_max_minutes": t.reminder_interval_max_minutes,
            "reminder_start_hour": t.reminder_start_hour,
            "reminder_end_hour": t.reminder_end_hour,
        })
    return ApiResponse(success=True, data=data)


@router.patch("/{task_id}", response_model=ApiResponse)
async def update_task(
    task_id: int,
    payload: UpdateTaskRequest,
    session: AsyncSession = Depends(get_session),
    task_service: TaskService = Depends(get_task_service),
    user_service: UserService = Depends(get_user_service),
    identity: Identity = Depends(verify_bot_or_mini_app),
):
    await ensure_actor_owns_telegram_id(identity, payload.telegram_id, session)
    user_id = await _resolve_user_id(user_service, payload.telegram_id)
    if user_id is None:
        return ApiResponse(success=False, message="Foydalanuvchi topilmadi")

    existing_task = await task_service.get_task(task_id)
    if existing_task is None:
        return ApiResponse(success=False, message="Vazifa topilmadi")

    await ensure_admin_for_group(user_id, existing_task.group_id, session)

    fields = payload.model_dump(exclude={"telegram_id"})
    task = await task_service.update_task(task_id, user_id, **fields)
    if task is None:
        return ApiResponse(success=False, message="Vazifa topilmadi")

    return ApiResponse(success=True, message="Vazifa yangilandi")


@router.delete("/{task_id}", response_model=ApiResponse)
async def delete_task(
    task_id: int,
    payload: AdminActionRequest,
    session: AsyncSession = Depends(get_session),
    task_service: TaskService = Depends(get_task_service),
    user_service: UserService = Depends(get_user_service),
    identity: Identity = Depends(verify_bot_or_mini_app),
):
    await ensure_actor_owns_telegram_id(identity, payload.telegram_id, session)
    user_id = await _resolve_user_id(user_service, payload.telegram_id)
    if user_id is None:
        return ApiResponse(success=False, message="Foydalanuvchi topilmadi")

    task = await task_service.get_task(task_id)
    if task is None:
        return ApiResponse(success=False, message="Vazifa topilmadi")

    await ensure_admin_for_group(user_id, task.group_id, session)

    ok = await task_service.delete_task(task_id, user_id)
    return ApiResponse(success=ok, message="Vazifa o'chirildi" if ok else "Vazifa topilmadi")


@router.get("/{task_id}/queue/preview", response_model=ApiResponse)
async def preview_queue(
    task_id: int,
    session: AsyncSession = Depends(get_session),
    service: QueueService = Depends(get_queue_service),
    task_service: TaskService = Depends(get_task_service),
    group_service: GroupService = Depends(get_group_service),
    identity: Identity = Depends(verify_bot_or_mini_app),
):
    task = await task_service.get_task(task_id)
    if task is None:
        return ApiResponse(success=False, message="Vazifa topilmadi")
    await ensure_actor_can_access_group(identity, task.group_id, session)

    entries = await service.preview_queue(task_id)
    group = await group_service._repo.get_by_id(task.group_id) if task else None
    timezone_str = group.timezone if group else "Asia/Tashkent"
    return ApiResponse(success=True, data=_entries_to_data(entries, task, timezone_str))


@router.get("/{task_id}/queue/full", response_model=ApiResponse)
async def full_queue(
    task_id: int,
    session: AsyncSession = Depends(get_session),
    service: QueueService = Depends(get_queue_service),
    task_service: TaskService = Depends(get_task_service),
    group_service: GroupService = Depends(get_group_service),
    identity: Identity = Depends(verify_bot_or_mini_app),
):
    """Navbatdagi BARCHA a'zolarni tartib bo'yicha qaytaradi (3 taga
    cheklanmagan) - navbat tartibini to'liq qayta belgilash (reorder) UI'si
    uchun kerak."""
    task = await task_service.get_task(task_id)
    if task is None:
        return ApiResponse(success=False, message="Vazifa topilmadi")
    await ensure_actor_can_access_group(identity, task.group_id, session)

    entries = await service.get_full_queue(task_id)
    group = await group_service._repo.get_by_id(task.group_id) if task else None
    timezone_str = group.timezone if group else "Asia/Tashkent"
    return ApiResponse(success=True, data=_entries_to_data(entries, task, timezone_str))


@router.post("/{task_id}/queue/skip", response_model=ApiResponse)
async def skip_current(
    task_id: int,
    payload: AdminActionRequest,
    session: AsyncSession = Depends(get_session),
    task_service: TaskService = Depends(get_task_service),
    user_service: UserService = Depends(get_user_service),
    identity: Identity = Depends(verify_bot_or_mini_app),
):
    await ensure_actor_owns_telegram_id(identity, payload.telegram_id, session)
    user_id = await _resolve_user_id(user_service, payload.telegram_id)
    if user_id is None:
        return ApiResponse(success=False, message="Foydalanuvchi topilmadi")

    task = await task_service.get_task(task_id)
    if task is None:
        return ApiResponse(success=False, message="Vazifa topilmadi")

    await ensure_admin_for_group(user_id, task.group_id, session)

    await task_service.admin_skip(task_id, user_id)
    return ApiResponse(success=True, message="Navbat o'tkazib yuborildi")


@router.post("/{task_id}/queue/swap", response_model=ApiResponse)
async def swap_members(
    task_id: int,
    payload: SwapRequest,
    session: AsyncSession = Depends(get_session),
    task_service: TaskService = Depends(get_task_service),
    user_service: UserService = Depends(get_user_service),
    identity: Identity = Depends(verify_bot_or_mini_app),
):
    await ensure_actor_owns_telegram_id(identity, payload.telegram_id, session)
    user_id = await _resolve_user_id(user_service, payload.telegram_id)
    if user_id is None:
        return ApiResponse(success=False, message="Foydalanuvchi topilmadi")

    task = await task_service.get_task(task_id)
    if task is None:
        return ApiResponse(success=False, message="Vazifa topilmadi")

    await ensure_admin_for_group(user_id, task.group_id, session)

    await task_service.admin_swap(task_id, user_id, payload.member_id_a, payload.member_id_b)
    return ApiResponse(success=True, message="A'zolar navbatda almashtirildi")


@router.post("/{task_id}/queue/reorder", response_model=ApiResponse)
async def reorder_queue(
    task_id: int,
    payload: ReorderRequest,
    session: AsyncSession = Depends(get_session),
    task_service: TaskService = Depends(get_task_service),
    user_service: UserService = Depends(get_user_service),
    identity: Identity = Depends(verify_bot_or_mini_app),
):
    """Butun navbat tartibini `member_ids` ro'yxati bo'yicha qayta
    belgilaydi - ro'yxat navbatdagi barcha a'zolarni o'z ichiga olishi
    shart (aks holda xato qaytadi, hech narsa o'zgarmaydi)."""
    await ensure_actor_owns_telegram_id(identity, payload.telegram_id, session)
    user_id = await _resolve_user_id(user_service, payload.telegram_id)
    if user_id is None:
        return ApiResponse(success=False, message="Foydalanuvchi topilmadi")

    task = await task_service.get_task(task_id)
    if task is None:
        return ApiResponse(success=False, message="Vazifa topilmadi")

    await ensure_admin_for_group(user_id, task.group_id, session)

    try:
        await task_service.admin_reorder(task_id, user_id, payload.member_ids)
    except ValueError as exc:
        return ApiResponse(success=False, message=str(exc))

    return ApiResponse(success=True, message="Navbat tartibi yangilandi")


@router.get("/member/{telegram_id}", response_model=ApiResponse)
async def get_my_tasks(
    telegram_id: int,
    group_id: int,
    session: AsyncSession = Depends(get_session),
    task_service: TaskService = Depends(get_task_service),
    user_service: UserService = Depends(get_user_service),
    group_service: GroupService = Depends(get_group_service),
    identity: Identity = Depends(verify_bot_or_mini_app),
):
    """Berilgan guruhda shu foydalanuvchi hozir navbatda turgan vazifalar."""
    from sqlalchemy import select
    from ....infrastructure.models.task import TaskAssignment, TaskStatus
    from ....utils.datetime_utils import local_date_to_utc_start

    await ensure_actor_owns_telegram_id(identity, telegram_id, session)
    user = await user_service.get_by_telegram_id(telegram_id)
    if user is None:
        return ApiResponse(success=False, message="Foydalanuvchi topilmadi")

    membership = await group_service.get_membership(user.id, group_id)
    if membership is None:
        return ApiResponse(success=False, message="Siz bu guruh a'zosi emassiz")

    tasks = await task_service.get_member_tasks(membership.id)

    group = await group_service._repo.get_by_id(group_id)
    group_timezone = group.timezone if group else "Asia/Tashkent"
    today = get_local_today(group_timezone)
    today_start_utc = local_date_to_utc_start(today, group_timezone)

    data = []
    for t in tasks:
        days_left = 0
        assignment_stmt = (
            select(TaskAssignment)
            .where(
                TaskAssignment.task_id == t.id,
                TaskAssignment.member_id == membership.id,
                TaskAssignment.assigned_date == today_start_utc,
                TaskAssignment.status.in_(
                    [TaskStatus.PENDING, TaskStatus.IN_PROGRESS, TaskStatus.OVERDUE]
                ),
            )
            .limit(1)
        )
        assignment_result = await session.execute(assignment_stmt)
        open_assignment = assignment_result.scalar_one_or_none()

        is_active_now = open_assignment is not None
        if not is_active_now and t.next_execution_date:
            next_local_date = utc_to_local_date(t.next_execution_date, group_timezone)
            days_left = (next_local_date - today).days

        data.append({
            "id": t.id,
            "name": t.name,
            "group_id": t.group_id,
            "days_left": days_left,
            "is_active_now": is_active_now,
            "next_execution_date": t.next_execution_date.isoformat() if t.next_execution_date else None
        })
    return ApiResponse(success=True, data=data)
