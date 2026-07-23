"""add_membership_and_assignment_unique_constraints

Bir foydalanuvchi bitta guruhda faqat bitta FAOL a'zolikka ega bo'lishi
(partial unique index, is_active=true bo'lganda) va bitta vazifa/a'zo/kun
uchun faqat bitta TaskAssignment yaratilishini DB darajasida ta'minlaydi.
Bu ikkalasi ham check-then-insert TOCTOU race'lar (masalan, ikki marta
tez-tez bosilgan "guruhga qo'shilish" so'rovi yoki bir vaqtda ishga
tushgan bir nechta scheduler jarayoni) natijasida dublikat qatorlar
paydo bo'lishining oldini oladi.

Revision ID: b1b1b1b1b1b1
Revises: a6a6a6a6a6a6
Create Date: 2026-07-21 03:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1b1b1b1b1b1'
down_revision: Union[str, None] = 'a6a6a6a6a6a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Har bir (user_id, group_id) juftligi uchun bir vaqtning o'zida
    # faqat bitta FAOL a'zolik bo'lishi mumkin (kelajakda "guruhdan
    # chiqish/qayta qo'shilish" funksiyasi qo'shilsa ham, eski (is_active=false)
    # qatorlar tarix sifatida saqlanib qoladi).
    op.create_index(
        "ux_members_user_group_active",
        "members",
        ["user_id", "group_id"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
    )

    # Bitta vazifa uchun bitta a'zoga bitta kunda faqat bitta assignment
    # yaratilishi mumkin - bir nechta scheduler jarayoni parallel ishlab
    # ketsa ham dublikat assignment/eslatma/jarima yaratilmasin.
    op.create_unique_constraint(
        "ux_task_assignments_task_member_date",
        "task_assignments",
        ["task_id", "member_id", "assigned_date"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "ux_task_assignments_task_member_date", "task_assignments", type_="unique"
    )
    op.drop_index("ux_members_user_group_active", table_name="members")
