"""
Service Layer: Vazifani rasm bilan yakunlash to'liq oqimi.

Oqim:
1. Bugungi assignment topiladi/yaratiladi.
2. Rasm diskka saqlanadi, TaskCompletion PENDING holatida yaratiladi.
3. Agar rasm bor, guruhda bajaruvchidan tashqari faol a'zolar bo'lib,
   guruh Telegram chatga bog'langan bo'lsa - bot rasmni ✅/❌ ovoz berish
   tugmalari bilan guruhga yuboradi (bot/handlers/votes.py). Bajaruvchidan
   tashqari a'zolarning YARMIDAN KO'PI "Ha" desa - navbat keyingi a'zoga
   o'tadi; yarmidan ko'pi "Yo'q" desa - vazifa SHU a'zoda qoladi, u
   qaytadan bajarishi kerak. Ovoz 2 soat davom etadi (`VotingService`) -
   shu muddatda ko'pchilik hosil bo'lmasa, scheduler yig'ilgan ovozlar
   bo'yicha avtomatik hal qiladi (`resolve_expired_votes`).
4. Aks holda (rasm yo'q, guruhda boshqa faol a'zo yo'q, yoki guruh
   Telegram chatga bog'lanmagan) - ovoz berishga hech kim/hech narsa
   yo'q, shuning uchun topshiriq DARHOL tasdiqlanadi.

TARIX: bu yerda avval ✅/❌ guruh ovoz berish bosqichi bor edi, keyin
1-5 yulduzli "sifat bahosi" bilan almashtirilgan edi (navbatga ta'sir
qilmaydigan alohida signal). Talab bo'yicha ovoz berish bosqichi
qaytarildi, yulduzli baho butunlay olib tashlandi.
"""

from datetime import datetime, timezone

from ..infrastructure.models.task import CompletionApprovalStatus, Task, TaskAssignment
from ..repositories.assignment_repository import AssignmentRepository
from ..repositories.group_repository import GroupRepository
from ..repositories.user_repository import UserRepository
from .notification_service import NotificationService
from .photo_storage_service import PhotoStorageService
from .task_service import TaskService
from .voting_service import (
    VOTE_WINDOW,
    Decision,
    SelfVoteError,
    VoteNotAllowedError,
    VoteWindowExpiredError,
    VotingService,
    decide,
    needed_for_majority,
    vote_window_closed,
)
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
        voting_service: VotingService | None = None,
    ) -> None:
        self._assignment_repo = assignment_repository
        self._group_repo = group_repository
        self._task_service = task_service
        self._photo_storage = photo_storage
        self._notification_service = notification_service
        self._user_repo = user_repository
        self._voting_service = voting_service

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
        needs_vote = bool(photo_bytes and eligible_total > 0 and group and group.telegram_chat_id)

        if not needs_vote:
            # Ovoz berishga hech kim/hech narsa yo'q - DARHOL tasdiqlanadi.
            await self._resolve(completion, assignment, task, member_id)
            return {
                "auto_approved": True,
                "completion_id": completion.id,
                "assignment_id": assignment.id,
                "photo_path": photo_path,
            }

        member = await self._group_repo.get_member_by_id(member_id)
        member_user = (
            await self._user_repo.get_by_id(member.user_id)
            if member and self._user_repo
            else None
        )
        return {
            "awaiting_vote": True,
            "completion_id": completion.id,
            "assignment_id": assignment.id,
            "photo_path": photo_path,
            "group_id": group.id,
            "telegram_chat_id": group.telegram_chat_id,
            "task_name": task.name,
            "member_name": member_user.full_name if member_user else None,
            "eligible_total": eligible_total,
            "needed": needed_for_majority(eligible_total),
        }

    async def submit_vote(
        self, completion_id: int, voter_telegram_id: int, approve: bool
    ) -> dict:
        """
        Guruh a'zosi PENDING topshiriqqa ✅/❌ ovoz beradi. Bajaruvchidan
        tashqari faol a'zolarning yarmidan ko'pi "Ha" desa - navbat
        keyingi a'zoga o'tadi; yarmidan ko'pi "Yo'q" desa - vazifa shu
        a'zoda qoladi (u qaytadan bajarishi kerak).
        """
        completion = await self._assignment_repo.get_completion_by_id(completion_id)
        if completion is None:
            raise CompletionNotFoundError()
        if completion.approval_status != CompletionApprovalStatus.PENDING:
            raise VoteNotAllowedError()
        if vote_window_closed(completion.completed_at):
            raise VoteWindowExpiredError()

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

        eligible_total = await self._group_repo.count_other_active_members(
            task.group_id, completion.member_id
        )
        tally = await self._voting_service.record_vote(
            completion_id=completion_id,
            voter_member_id=voter_member.id,
            approve=approve,
            eligible_total=eligible_total,
        )

        resolution: Decision | None = tally["resolution"]
        if resolution == "approved":
            await self._resolve(completion, assignment, task, completion.member_id)
        elif resolution == "rejected":
            await self._reject(completion, assignment)

        assignee_member = await self._group_repo.get_member_by_id(completion.member_id)
        assignee_user = (
            await self._user_repo.get_by_id(assignee_member.user_id) if assignee_member else None
        )

        return {
            **tally,
            "task_name": task.name,
            "assignee_name": assignee_user.full_name if assignee_user else None,
            "assignee_telegram_id": assignee_user.telegram_id if assignee_user else None,
        }

    async def resolve_expired_votes(self) -> list[dict]:
        """
        2 soatlik ovoz berish oynasi tugagan, lekin hali PENDING qolgan
        topshiriqlarni yig'ilgan ovozlar bo'yicha yakunlaydi. Scheduler
        davriy chaqiradi (`scheduler/jobs.py`).
        """
        cutoff = datetime.now(timezone.utc) - VOTE_WINDOW
        expired = await self._assignment_repo.list_expired_pending_completions(cutoff)

        results: list[dict] = []
        for completion in expired:
            assignment = await self._assignment_repo.get_by_id(completion.assignment_id)
            task = await self._task_service.get_task(assignment.task_id) if assignment else None
            if assignment is None or task is None:
                continue

            eligible_total = await self._group_repo.count_other_active_members(
                task.group_id, completion.member_id
            )
            yes, no = await self._voting_service.tally(completion.id)
            resolution = decide(eligible_total, yes, no, timed_out=True)

            if resolution == "approved":
                await self._resolve(completion, assignment, task, completion.member_id)
            else:
                await self._reject(completion, assignment)

            group = await self._group_repo.get_by_id(task.group_id)
            assignee_member = await self._group_repo.get_member_by_id(completion.member_id)
            assignee_user = (
                await self._user_repo.get_by_id(assignee_member.user_id)
                if assignee_member
                else None
            )
            results.append(
                {
                    "completion_id": completion.id,
                    "resolution": resolution,
                    "task_name": task.name,
                    "group_id": task.group_id,
                    "telegram_chat_id": group.telegram_chat_id if group else None,
                    "assignee_name": assignee_user.full_name if assignee_user else None,
                    "assignee_telegram_id": assignee_user.telegram_id if assignee_user else None,
                    "yes": yes,
                    "no": no,
                }
            )
        return results

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

    async def _reject(self, completion, assignment: TaskAssignment) -> None:
        await self._assignment_repo.resolve_completion(
            completion, CompletionApprovalStatus.REJECTED
        )
        await self._assignment_repo.revert_to_pending(assignment)
