"""add_reminder_interval_range

Eslatma intervali endi bitta qat'iy son emas, min-max oralig'i:
- reminder_interval_minutes -> reminder_interval_min_minutes / reminder_interval_max_minutes.
- Mavjud vazifalar uchun eski qiymat ikkalasiga ham nusxalanadi (xatti-harakat o'zgarmaydi).

Revision ID: d4d4d4d4d4d4
Revises: c3c3c3c3c3c3
Create Date: 2026-07-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4d4d4d4d4d4'
down_revision: Union[str, None] = 'c3c3c3c3c3c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("reminder_interval_min_minutes", sa.Integer(), nullable=True),
    )
    op.add_column(
        "tasks",
        sa.Column("reminder_interval_max_minutes", sa.Integer(), nullable=True),
    )

    op.execute(
        "UPDATE tasks SET reminder_interval_min_minutes = reminder_interval_minutes, "
        "reminder_interval_max_minutes = reminder_interval_minutes"
    )

    op.alter_column(
        "tasks", "reminder_interval_min_minutes", nullable=False, server_default="60"
    )
    op.alter_column(
        "tasks", "reminder_interval_max_minutes", nullable=False, server_default="60"
    )

    op.drop_column("tasks", "reminder_interval_minutes")


def downgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("reminder_interval_minutes", sa.Integer(), nullable=True),
    )
    op.execute(
        "UPDATE tasks SET reminder_interval_minutes = reminder_interval_min_minutes"
    )
    op.alter_column(
        "tasks", "reminder_interval_minutes", nullable=False, server_default="60"
    )
    op.drop_column("tasks", "reminder_interval_max_minutes")
    op.drop_column("tasks", "reminder_interval_min_minutes")
