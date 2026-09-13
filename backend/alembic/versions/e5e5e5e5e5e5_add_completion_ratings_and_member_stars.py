"""add_completion_ratings_and_member_stars

Foydalanuvchi profili uchun 5 yulduzli reyting tizimi:

- completion_ratings: guruh a'zosi bajarilgan (tasdiqlangan) vazifaga
  1-5 yulduz bilan baho beradi (sifat/tezlik bahosi - approve/reject
  ovozidan alohida). Bir a'zo bitta topshiriqqa faqat bir marta baho
  beradi (completion_votes bilan bir xil unique naqsh).
- members.rating_stars_cache: hisoblangan yakuniy daraja keshi (5.0 dan
  boshlanadi). Har safar yangi baho kelganda yoki jarima qo'shilganda
  qayta hisoblab shu yerga yoziladi - profil sahifasini har safar
  o'rtachani butun tarix bo'yicha qayta hisoblashga majburlamaslik uchun.

Revision ID: e5e5e5e5e5e5
Revises: d4d4d4d4d4d4
Create Date: 2026-09-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5e5e5e5e5e5'
down_revision: Union[str, None] = 'd4d4d4d4d4d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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

    # Yakuniy daraja keshi: 5.0 dan boshlanadi, har bir a'zo uchun.
    op.add_column(
        "members",
        sa.Column(
            "rating_stars_cache",
            sa.Numeric(3, 2),
            nullable=False,
            server_default="5.00",
        ),
    )


def downgrade() -> None:
    op.drop_column("members", "rating_stars_cache")
    op.drop_constraint(
        "ux_completion_ratings_completion_rater", "completion_ratings", type_="unique"
    )
    op.drop_table("completion_ratings")
