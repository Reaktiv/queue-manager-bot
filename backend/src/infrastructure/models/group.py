"""
Guruh (uy/ofis/jamoa) va a'zolik modellari.

Har bir guruh mustaqil: o'z a'zolari, vazifalari, navbatlari, sozlamalari.
"""

import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Index, Numeric, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.session import Base

if TYPE_CHECKING:
    from .task import Task
    from .user import User


class MemberRole(str, enum.Enum):
    ADMIN = "admin"
    MEMBER = "member"


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    telegram_chat_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True)

    invite_code: Mapped[str] = mapped_column(String(16), unique=True, index=True, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Tashkent", nullable=False)

    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_active: Mapped[bool] = mapped_column(default=True)

    members: Mapped[list["Member"]] = relationship(back_populates="group")
    tasks: Mapped[list["Task"]] = relationship(back_populates="group")


class Member(Base):
    """Foydalanuvchining ma'lum bir guruhdagi a'zoligi (rol, holat)."""

    __tablename__ = "members"
    __table_args__ = (
        Index(
            "ux_members_user_group_active",
            "user_id",
            "group_id",
            unique=True,
            postgresql_where=text("is_active = true"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False)

    role: Mapped[MemberRole] = mapped_column(Enum(MemberRole), default=MemberRole.MEMBER)

    is_on_vacation: Mapped[bool] = mapped_column(default=False)
    vacation_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    rating_stars_cache: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=Decimal("5.00"))
    """
    Foydalanuvchi profilidagi yakuniy daraja (1.00 - 5.00), 5.00 dan
    boshlanadi. `RatingService` tomonidan har safar yangi baho kelganda
    yoki jarima qo'shilganda qayta hisoblanadi:
        daraja = clamp(guruhdoshlar bergan o'rtacha ball - jarima soni, 1, 5)
    Bu ustun faqat KESH - har safar profilni ochganda butun tarixni qayta
    yig'ib hisoblash shart bo'lmasin deb saqlanadi.
    """

    user: Mapped["User"] = relationship(back_populates="memberships")
    group: Mapped["Group"] = relationship(back_populates="members")
