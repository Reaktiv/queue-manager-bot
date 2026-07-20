"""
Service Layer: Vazifani rasm bilan yakunlash to'liq oqimi.

Oqim:
1. Bugungi assignment topiladi/yaratiladi.
2. Rasm diskka saqlanadi.
3. TaskCompletion yozuvi yaratiladi (tarix uchun - hech qachon o'chmaydi).
4. Assignment "completed" statusiga o'tadi.
5. Navbat bir qadam suriladi (TaskService orqali - Queue Lock ochiladi).
6. Guruhga bildirishnoma yuboriladi.
"""

from ..infrastructure.models.task import Task
from ..repositories.assignment_repository import AssignmentRepository
from ..repositories.group_repository import GroupRepository
from .notification_service import NotificationService
from .photo_storage_service import PhotoStorageService
from .task_service import TaskService
from ..utils.datetime_utils import get_local_today


class NotQueueOwnerError(Exception):
    """A'zo hozir navbatning boshida turmagani uchun vazifani bajara olmaydi."""


class CompletionService:
    def __init__(
        self,
        assignment_repository: AssignmentRepository,
        group_repository: GroupRepository,
        task_service: TaskService,
        photo_storage: PhotoStorageService,
        notification_service: NotificationService,
    ) -> None:
        self._assignment_repo = assignment_repository
        self._group_repo = group_repository
        self._task_service = task_service
        self._photo_storage = photo_storage
        self._notification_service = notification_service

    async def complete_with_photo(
        self,
        task: Task,
        member_id: int,
        photo_bytes: bytes | None,
        photo_filename: str | None,
        caption: str | None,
    ) -> dict:
        # Diqqat: navbat qulflash qoidasi - faqat boshda turgan a'zo bajara oladi
        current_entry = await self._task_service.get_queue_preview(task.id)
        if not current_entry or current_entry[0].member_id != member_id:
            raise NotQueueOwnerError()

        if task.require_photo and not photo_bytes:
            raise ValueError("Bu vazifa uchun rasm majburiy")

        photo_path = None
        if photo_bytes:
            photo_path = self._photo_storage.save_photo(
                photo_bytes, photo_filename or "photo.jpg", task.id
            )

        group = await self._group_repo.get_by_id(task.group_id)
        timezone_str = group.timezone if group else "Asia/Tashkent"
        assignment = await self._assignment_repo.get_or_create_for_local_date(
            task.id,
            member_id,
            get_local_today(timezone_str),
            timezone_str,
        )
        await self._assignment_repo.add_completion_record(
            assignment_id=assignment.id,
            member_id=member_id,
            photo_path=photo_path,
            caption=caption,
        )
        await self._assignment_repo.mark_completed(assignment)

        await self._task_service.complete_task(task.id, member_id)

        # Yangi navbatdagi a'zoga xabar berish uchun tayyorlik (bot orqali yuboriladi)
        new_queue = await self._task_service.get_queue_preview(task.id)
        next_member_id = new_queue[0].member_id if new_queue else None

        return {
            "assignment_id": assignment.id,
            "photo_path": photo_path,
            "next_member_id": next_member_id,
        }
