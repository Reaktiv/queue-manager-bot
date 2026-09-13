"""
Barcha SQLAlchemy modellarini shu yerga import qilamiz, shunda:
1. Alembic autogenerate barcha jadvallarni ko'radi.
2. Boshqa modullar `from src.infrastructure.models import User, Group, ...` deb ishlata oladi.
"""

from .audit import AuditLog, NotificationTemplate
from .group import Group, Member, MemberRole
from .settings import SystemLog, SystemSetting
from .task import (
    CompletionApprovalStatus,
    CompletionRating,
    CompletionVote,
    Penalty,
    ScheduleType,
    Task,
    TaskAssignment,
    TaskCompletion,
    TaskQueueEntry,
    TaskStatus,
)
from .user import User

__all__ = [
    "AuditLog",
    "NotificationTemplate",
    "CompletionApprovalStatus",
    "CompletionRating",
    "CompletionVote",
    "Group",
    "Member",
    "MemberRole",
    "Penalty",
    "ScheduleType",
    "SystemLog",
    "SystemSetting",
    "Task",
    "TaskAssignment",
    "TaskCompletion",
    "TaskQueueEntry",
    "TaskStatus",
    "User",
]
