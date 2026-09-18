"""
Vazifa, navbat va bajarish tarixi modellari.

Har bir vazifaning o'z mustaqil navbati bor - navbatlar bir-biriga
ta'sir qilmaydi (masalan, "Oshxona" navbati "Axlat" navbatidan alohida).
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.session import Base

if TYPE_CHECKING:
    from .group import Group, Member


class ScheduleType(str, enum.Enum):
    DAILY = "daily"
    EVERY_X_DAYS = "every_x_days"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM_CRON = "custom_cron"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"


class CompletionApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)

    schedule_type: Mapped[ScheduleType] = mapped_column(default=ScheduleType.DAILY)
    schedule_interval_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    schedule_cron: Mapped[str | None] = mapped_column(String(128), nullable=True)

    reminder_interval_min_minutes: Mapped[int] = mapped_column(Integer, default=60)
    reminder_interval_max_minutes: Mapped[int] = mapped_column(Integer, default=60)
    reminder_start_hour: Mapped[int] = mapped_column(Integer, default=8)
    reminder_end_hour: Mapped[int] = mapped_column(Integer, default=22)

    require_photo: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_execution_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_reminder_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_pre_warning_sent_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    group: Mapped["Group"] = relationship(back_populates="tasks")
    queue_entries: Mapped[list["TaskQueueEntry"]] = relationship(
        back_populates="task", order_by="TaskQueueEntry.position"
    )


class TaskQueueEntry(Base):
    """Vazifaning navbatidagi bitta pozitsiya (a'zo + tartib raqami)."""

    __tablename__ = "task_queue"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    """Navbat qulflanganda - shu a'zo vazifani bajarmaguncha keyingisiga o'tmaydi."""

    task: Mapped["Task"] = relationship(back_populates="queue_entries")
    member: Mapped["Member"] = relationship("Member")


class TaskAssignment(Base):
    """Ma'lum bir kunga tayinlangan vazifa nusxasi (bugungi/kechagi holat)."""

    __tablename__ = "task_assignments"
    __table_args__ = (
        UniqueConstraint(
            "task_id", "member_id", "assigned_date", name="ux_task_assignments_task_member_date"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), nullable=False)

    assigned_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(default=TaskStatus.PENDING)

    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completion_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TaskCompletion(Base):
    """Bajarilgan vazifa haqida to'liq tarixiy yozuv (rasm bilan)."""

    __tablename__ = "task_completion"

    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("task_assignments.id"), nullable=False)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), nullable=False)

    photo_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    approval_status: Mapped[CompletionApprovalStatus] = mapped_column(
        default=CompletionApprovalStatus.PENDING
    )
    """Guruh a'zolari ovoz berish holati - rasm faqat tasdiqlangach "haqiqiy" bajarish hisoblanadi."""
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    votes: Mapped[list["CompletionVote"]] = relationship(back_populates="completion")


class CompletionVote(Base):
    """Guruh a'zosining bitta TaskCompletion uchun bergan ovozi (tasdiqlash/rad etish)."""

    __tablename__ = "completion_votes"
    __table_args__ = (
        UniqueConstraint(
            "completion_id", "voter_member_id", name="ux_completion_votes_completion_voter"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    completion_id: Mapped[int] = mapped_column(ForeignKey("task_completion.id"), nullable=False)
    voter_member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), nullable=False)
    approve: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    completion: Mapped["TaskCompletion"] = relationship(back_populates="votes")
