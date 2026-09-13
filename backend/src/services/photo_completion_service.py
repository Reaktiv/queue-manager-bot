"""
Service Layer: Vazifani rasm bilan yakunlash to'liq oqimi.

Oqim (yangi - guruh tasdig'i bilan):
1. Bugungi assignment topiladi/yaratiladi.
2. Rasm diskka saqlanadi.
3. TaskCompletion yozuvi yaratiladi (approval_status=PENDING, tarix uchun - hech
   qachon o'chmaydi).
4. Assignment "in_progress" statusiga o'tadi (navbat hali suriladi, lekin
   COMPLETED emas - guruh tasdiqlashi kerak).
5. Agar rasm shart bo'lmasa yoki guruhda ovoz bera oladigan boshqa a'zo bo'lmasa
   (yoki guruh Telegram chatga bog'lanmagan bo'lsa) - avtomatik tasdiqlanadi.
6. Aks holda bot rasmni guruhga ✅/❌ tugmalar bilan yuboradi; a'zolarning
   50%+ "ha" desa - tasdiqlanadi va navbat suriladi (TaskService orqali);
   50%+ "yo'q" desa - rad etiladi, vazifa o'sha a'zoning o'zida qoladi va
   uni qayta bajarishi haqida xabar beriladi.
"""

from ..infrastructure.models.task import CompletionApprovalStatus, Task, TaskAssignment
from ..repositories.assignment_repository import AssignmentRepository
from ..repositories.completion_vote_repository import CompletionVoteRepository
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


class AlreadyResolvedError(Exception):
    """Bu topshiriq allaqachon tasdiqlangan yoki rad etilgan - qayta ovoz berish mumkin emas."""


class NotGroupMemberError(Exception):
    pass


class SelfVoteError(Exception):
    """A'zo o'zi bajargan vazifaga o'zi ovoz bera olmaydi."""


class CompletionService:
    def __init__(
        self,
        assignment_repository: AssignmentRepository,
        group_repository: GroupRepository,
        task_service: TaskService,
        photo_storage: PhotoStorageService,
        notification_service: NotificationService,
        user_repository: UserRepository | None = None,
        vote_repository: CompletionVoteRepository | None = None,
        rating_service: RatingService | None = None,
    ) -> None:
        self._assignment_repo = assignment_repository
        self._group_repo = group_repository
        self._task_service = task_service
        self._photo_storage = photo_storage
        self._notification_service = notification_service
        self._user_repo = user_repository
        self._vote_repo = vote_repository
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

        eligible_total = await self._group_repo.count_other_active_members(
            task.group_id, member_id
        )
        needs_group_vote = bool(photo_bytes) and eligible_total > 0 and bool(
            group and group.telegram_chat_id
        )

        if not needs_group_vote:
            await self._resolve(completion, assignment, task, member_id, approved=True)
            return {
                "auto_approved": True,
                "assignment_id": assignment.id,
                "photo_path": photo_path,
            }

        member = await self._group_repo.get_member_by_id(member_id)
        member_user = await self._user_repo.get_by_id(member.user_id) if member and self._user_repo else None

        return {
            "auto_approved": False,
            "completion_id": completion.id,
            "assignment_id": assignment.id,
            "photo_path": photo_path,
            "group_id": group.id,
            "telegram_chat_id": group.telegram_chat_id,
            "task_name": task.name,
            "member_name": member_user.full_name if member_user else None,
            "eligible_total": eligible_total,
        }

    async def register_vote(
        self, completion_id: int, voter_telegram_id: int, approve: bool
    ) -> dict:
        completion = await self._assignment_repo.get_completion_by_id(completion_id)
        if completion is None:
            raise CompletionNotFoundError()
        if completion.approval_status != CompletionApprovalStatus.PENDING:
            raise AlreadyResolvedError()

        assignment = await self._assignment_repo.get_by_id(completion.assignment_id)
        if assignment is None:
            raise CompletionNotFoundError()
        task = await self._task_service.get_task(assignment.task_id)
        if task is None:
            raise CompletionNotFoundError()

        voter_user = await self._user_repo.get_by_telegram_id(voter_telegram_id)
        if voter_user is None:
            raise NotGroupMemberError()
        voter_member = await self._group_repo.get_membership(voter_user.id, task.group_id)
        if voter_member is None or not voter_member.is_active:
            raise NotGroupMemberError()
        if voter_member.id == completion.member_id:
            raise SelfVoteError()

        await self._vote_repo.upsert_vote(completion_id, voter_member.id, approve)
        yes_count, no_count = await self._vote_repo.count_votes(completion_id)
        eligible_total = await self._group_repo.count_other_active_members(
            task.group_id, completion.member_id
        )

        status = "pending"
        if eligible_total > 0 and yes_count / eligible_total > 0.5:
            await self._resolve(completion, assignment, task, completion.member_id, approved=True)
            status = "approved"
        elif eligible_total > 0 and no_count / eligible_total > 0.5:
            await self._resolve(completion, assignment, task, completion.member_id, approved=False)
            status = "rejected"

        assignee_member = await self._group_repo.get_member_by_id(completion.member_id)
        assignee_user = (
            await self._user_repo.get_by_id(assignee_member.user_id) if assignee_member else None
        )

        return {
            "status": status,
            "yes_count": yes_count,
            "no_count": no_count,
            "eligible_total": eligible_total,
            "task_name": task.name,
            "assignee_telegram_id": assignee_user.telegram_id if assignee_user else None,
            "assignee_name": assignee_user.full_name if assignee_user else None,
        }

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
        approved: bool,
    ) -> None:
        if approved:
            await self._assignment_repo.resolve_completion(
                completion, CompletionApprovalStatus.APPROVED
            )
            await self._assignment_repo.mark_completed(assignment)
            await self._task_service.complete_task(task.id, member_id)
        else:
            await self._assignment_repo.resolve_completion(
                completion, CompletionApprovalStatus.REJECTED
            )
            await self._assignment_repo.mark_pending(assignment)
