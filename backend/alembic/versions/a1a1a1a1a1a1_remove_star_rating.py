"""remove_star_rating

Yulduzli sifat bahosi tizimi Ha/Yo'q guruh ovoz berish bilan almashtirildi
(`completion_votes`/`CompletionApprovalStatus` allaqachon mavjud, migration
`c3c3c3c3c3c3`). Endi kerak bo'lmagan qismlar olib tashlanadi:
- completion_ratings jadvali.
- members.rating_stars_cache ustuni (o'rniga faqat xom jarima balli qoladi).

Revision ID: a1a1a1a1a1a1
Revises: f6f6f6f6f6f6
Create Date: 2026-09-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1a1a1a1a1a1'
down_revision: Union[str, None] = 'f6f6f6f6f6f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "ux_completion_ratings_completion_rater", "completion_ratings", type_="unique"
    )
    op.drop_table("completion_ratings")
    op.drop_column("members", "rating_stars_cache")


def downgrade() -> None:
    op.add_column(
        "members",
        sa.Column(
            "rating_stars_cache",
            sa.Numeric(3, 2),
            nullable=False,
            server_default="5.00",
        ),
    )
    op.create_table(
        "completion_ratings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "completion_id", sa.Integer(), sa.ForeignKey("task_completion.id"), nullable=False
        ),
        sa.Column("rater_member_id", sa.Integer(), sa.ForeignKey("members.id"), nullable=False),
        sa.Column("stars", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_unique_constraint(
        "ux_completion_ratings_completion_rater",
        "completion_ratings",
        ["completion_id", "rater_member_id"],
    )
