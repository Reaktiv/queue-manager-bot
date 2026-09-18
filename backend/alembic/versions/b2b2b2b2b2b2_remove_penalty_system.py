"""remove_penalty_system

Jarima (Penalty) tizimi butunlay olib tashlanadi - vazifa muddati o'tsa
endi ball hisoblanmaydi, o'rniga a'zoga ertasi kundan boshlab har 1
soatda eslatma yuboriladi (guruh + shaxsiy chat). Sof statistika uchun
kerakli so'rovlar (`get_completion_stats`, `count_all_completions`)
`AssignmentRepository`ga ko'chirildi - ular `penalties` jadvaliga emas,
`task_assignments`/`task_completion`ga tayanadi.

Revision ID: b2b2b2b2b2b2
Revises: a1a1a1a1a1a1
Create Date: 2026-09-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2b2b2b2b2b2'
down_revision: Union[str, None] = 'a1a1a1a1a1a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("penalties")


def downgrade() -> None:
    op.create_table(
        "penalties",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("member_id", sa.Integer(), sa.ForeignKey("members.id"), nullable=False),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column(
            "assignment_id", sa.Integer(), sa.ForeignKey("task_assignments.id"), nullable=False
        ),
        sa.Column("points", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "reason", sa.String(length=255), nullable=False, server_default="missed_deadline"
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
