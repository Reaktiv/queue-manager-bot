"""add_user_phone_number

Doimiy reply keyboard'dagi "Profil" bo'limi uchun: foydalanuvchining
telefon raqami. Telegram botlar boshqa birovning raqamini so'ray
olmaydi - faqat foydalanuvchining O'ZI "kontakt ulashish" tugmasi
orqali bergan raqamini olamiz, shuning uchun ustun har doim NULL
bo'lishi mumkin (hali ulashmagan foydalanuvchilar uchun).

Revision ID: f6f6f6f6f6f6
Revises: e5e5e5e5e5e5
Create Date: 2026-09-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6f6f6f6f6f6'
down_revision: Union[str, None] = 'e5e5e5e5e5e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("phone_number", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "phone_number")
