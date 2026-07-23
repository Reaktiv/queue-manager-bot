"""add_completion_approval_voting

Vazifani rasm bilan bajarish endi darhol yakunlanmaydi - guruh a'zolari
ovoz berib tasdiqlashi (yoki rad etishi) kerak:
- task_completion.approval_status (pending/approved/rejected) va resolved_at.
- completion_votes: har bir a'zoning bitta topshiriq uchun ovozi (unique).

Revision ID: c3c3c3c3c3c3
Revises: b1b1b1b1b1b1
Create Date: 2026-07-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3c3c3c3c3c3'
down_revision: Union[str, None] = 'b1b1b1b1b1b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    approval_status_enum = sa.Enum(
        "PENDING", "APPROVED", "REJECTED", name="completionapprovalstatus"
    )
    approval_status_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "task_completion",
        sa.Column(
            "approval_status",
            approval_status_enum,
            nullable=False,
            server_default="PENDING",
        ),
    )
    op.add_column(
        "task_completion",
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Mavjud (eski) yozuvlar allaqachon yakunlangan hisoblanadi - ular oldindan
    # tasdiqlangan deb belgilanadi, aks holda tarixiy hisobotlar buzilib qoladi.
    op.execute("UPDATE task_completion SET approval_status = 'APPROVED', resolved_at = completed_at")

    op.create_table(
        "completion_votes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "completion_id", sa.Integer(), sa.ForeignKey("task_completion.id"), nullable=False
        ),
        sa.Column("voter_member_id", sa.Integer(), sa.ForeignKey("members.id"), nullable=False),
        sa.Column("approve", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_unique_constraint(
        "ux_completion_votes_completion_voter",
        "completion_votes",
        ["completion_id", "voter_member_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "ux_completion_votes_completion_voter", "completion_votes", type_="unique"
    )
    op.drop_table("completion_votes")
    op.drop_column("task_completion", "resolved_at")
    op.drop_column("task_completion", "approval_status")
    sa.Enum(name="completionapprovalstatus").drop(op.get_bind(), checkfirst=True)
