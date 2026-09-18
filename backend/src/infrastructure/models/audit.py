"""
Audit log va bildirishnoma shablonlari.

Har bir muhim harakat shu yerga yoziladi - tarix hech qachon o'chirilmaydi.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..db.session import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int | None] = mapped_column(ForeignKey("groups.id"), nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    action: Mapped[str] = mapped_column(String(64), nullable=False)
    """Masalan: task_created, queue_updated, task_marked_overdue, member_joined."""

    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[int | None] = mapped_column(nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NotificationTemplate(Base):
    __tablename__ = "notification_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False)

    template_type: Mapped[str] = mapped_column(String(64), nullable=False)
    """reminder | completed | overdue | queue_changed | task_assigned"""

    text_template: Mapped[str] = mapped_column(Text, nullable=False)
    """Placeholder qo'llab-quvvatlanadi: {user}, {task}, {group}, {date}"""

    language: Mapped[str] = mapped_column(String(8), default="uz")
