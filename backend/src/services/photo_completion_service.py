"""
Service Layer: Vazifani rasm bilan yakunlash to'liq oqimi.

Oqim:
1. Bugungi assignment topiladi/yaratiladi.
2. Rasm diskka saqlanadi.
3. TaskCompletion yozuvi yaratiladi va DARHOL tasdiqlanadi (APPROVED) -
   navbat shu zahoti keyingi a'zoga o'tadi.
4. Agar rasm bor va guruhda boshqa faol a'zolar bo'lib, guruh Telegram
   chatga bog'langan bo'lsa - bot rasmni guruhga 1-5 yulduz baholash
   tugmalari bilan yuboradi (bot/handlers/my_tasks.py). Bu ENDI
   "bajarildimi?" degan tasdiqlash EMAS - faqat "qanday bajarildi?"
   degan sifat bahosi (`RatingService`), vazifaning bajarilishiga
   ta'sir qilmaydi.

TARIX: ilgari bu yerda guruh a'zolari ✅/❌ ovoz berib, ko'pchilik "ha"
desagina navbat suriladigan alohida bosqich bor edi (`register_vote`,
`CompletionVote`). Talab bo'yicha bu bosqich olib tashlandi - endi
bittagina bajaruvchi rasm yuborsa kifoya, boshqalar faqat sifatini
baholaydi.
"""

from ..infrastructure.models.task import CompletionApprovalStatus, Task, TaskAssignment
from ..repositories.assignment_repository import AssignmentRepository
from ..repositories.group_repository import GroupRepository
from ..repositories.user_repository import UserRepository
from .notification_service import NotificationService
from .photo_storage_service import PhotoStorageService
from .rating_service import (
    RatingNotAllowedError,
    RatingService,
    RatingWindowExpiredError,
    SelfRatingError,
    rating_window_closed,
)
from .task_service import TaskService
from ..utils.datetime_utils import get_local_today


class NotQueueOwnerError(Exception):
    """A'zo hozir navbatning boshida turmagani uchun vazifani bajara olmaydi."""


class PendingApprovalError(Exception):
    """Shu vazifa uchun oldingi rasm hali guruh tomonidan hal qilinmagan."""


class CompletionNotFoundError(Exception):
    pass


class NotGroupMemberError(Exception):
    pass


class CompletionService:
    def __init__(
        self,
        assignment_repository: AssignmentRepository,
        group_repository: GroupRepository,
        task_service: TaskService,
        photo_storage: PhotoStorageService,
        notification_service: NotificationService,
        user_repository: UserRepository | None = None,
        rating_service: RatingService | None = None,
    ) -> None:
        self._assignment_repo = assignment_repository
        self._group_repo = group_repository
        self._task_service = task_service
        self._photo_storage = photo_storage
        self._notification_service = notification_service
        self._user_repo = user_repository
        self._rating_service = rating_service

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

        group = await self._group_repo.get_by_id(task.group_id)
        timezone_str = group.timezone if group else "Asia/Tashkent"
        assignment = await self._assignment_repo.get_or_create_for_local_date(
            task.id,
            member_id,
            get_local_today(timezone_str),
            timezone_str,
        )

        existing_pending = await self._assignment_repo.get_pending_completion(assignment.id)
        if existing_pending is not None:
            raise PendingApprovalError()

        photo_path = None
        if photo_bytes:
            photo_path = self._photo_storage.save_photo(
                photo_bytes, photo_filename or "photo.jpg", task.id
            )

        completion = await self._assignment_repo.add_completion_record(
            assignment_id=assignment.id,
            member_id=member_id,
            photo_path=photo_path,
            caption=caption,
        )
        await self._assignment_repo.mark_in_progress(assignment)

        # Guruh tasdig'i YO'Q - vazifa DARHOL tasdiqlanadi, navbat shu
        # zahoti keyingi a'zoga o'tadi.
        await self._resolve(completion, assignment, task, member_id)

        result = {
            "auto_approved": True,
            "completion_id": completion.id,
            "assignment_id": assignment.id,
            "photo_path": photo_path,
        }

        # Rasm bor va guruhda baholay oladigan boshqa a'zo bo'lsa - bot
        # guruhga rasmni yulduz baholash tugmalari bilan yuborishi uchun
        # kerakli ma'lumotlar qo'shiladi. Bular vazifa allaqachon
        # tasdiqlangandan KEYIN, faqat sifat bahosi uchun.
        eligible_total = await self._group_repo.count_other_active_members(
            task.group_id, member_id
        )
        if photo_bytes and eligible_total > 0 and group and group.telegram_chat_id:
            member = await self._group_repo.get_member_by_id(member_id)
            member_user = (
                await self._user_repo.get_by_id(member.user_id)
                if member and self._user_repo
                else None
            )
            result.update(
                {
                    "group_id": group.id,
                    "telegram_chat_id": group.telegram_chat_id,
                    "task_name": task.name,
                    "member_name": member_user.full_name if member_user else None,
                    "eligible_total": eligible_total,
                }
            )

        return result

    async def submit_rating(
        self, completion_id: int, rater_telegram_id: int, stars: int
    ) -> dict:
        """
        Guruh a'zosi TASDIQLANGAN (approved) topshiriqqa 1-5 yulduz bilan
        sifat bahosi qo'yadi. Bu `register_vote` dagi ✅/❌ ovozdan alohida:
        vote "bajarildimi?" ga, rating "qanday bajarildi?" ga javob beradi -
        shuning uchun faqat allaqachon TASDIQLANGAN topshiriqqa baho berish
        mumkin (hali hal qilinmagan yoki rad etilganga emas).
        """
        completion = await self._assignment_repo.get_completion_by_id(completion_id)
        if completion is None:
            raise CompletionNotFoundError()
        if completion.approval_status != CompletionApprovalStatus.APPROVED:
            raise RatingNotAllowedError()
        if rating_window_closed(completion.resolved_at):
            raise RatingWindowExpiredError()

        assignment = await self._assignment_repo.get_by_id(completion.assignment_id)
        if assignment is None:
            raise CompletionNotFoundError()
        task = await self._task_service.get_task(assignment.task_id)
        if task is None:
            raise CompletionNotFoundError()

        rater_user = await self._user_repo.get_by_telegram_id(rater_telegram_id)
        if rater_user is None:
            raise NotGroupMemberError()
        rater_member = await self._group_repo.get_membership(rater_user.id, task.group_id)
        if rater_member is None or not rater_member.is_active:
            raise NotGroupMemberError()
        if rater_member.id == completion.member_id:
            raise SelfRatingError()

        result = await self._rating_service.record_rating(
            completion_id=completion_id,
            rater_member_id=rater_member.id,
            rated_member_id=completion.member_id,
            stars=stars,
        )

        assignee_member = await self._group_repo.get_member_by_id(completion.member_id)
        assignee_user = (
            await self._user_repo.get_by_id(assignee_member.user_id) if assignee_member else None
        )

        return {
            **result,
            "task_name": task.name,
            "assignee_name": assignee_user.full_name if assignee_user else None,
        }

    async def _resolve(
        self,
        completion,
        assignment: TaskAssignment,
        task: Task,
        member_id: int,
    ) -> None:
        await self._assignment_repo.resolve_completion(
            completion, CompletionApprovalStatus.APPROVED
        )
        await self._assignment_repo.mark_completed(assignment)
        await self._task_service.complete_task(task.id, member_id)
