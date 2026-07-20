"""add_last_pre_warning_sent_date

Revision ID: a6a6a6a6a6a6
Revises: 719a677ab6f0
Create Date: 2026-07-08 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a6a6a6a6a6a6'
down_revision: Union[str, None] = '719a677ab6f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tasks', sa.Column('last_pre_warning_sent_date', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('tasks', 'last_pre_warning_sent_date')
