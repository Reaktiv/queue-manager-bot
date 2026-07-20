"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-05

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("language", sa.String(length=8), nullable=False, server_default="uz"),
        sa.Column("is_super_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)

    # --- groups ---
    op.create_table(
        "groups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=True),
        sa.Column("invite_code", sa.String(length=16), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="Asia/Tashkent"),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_groups_invite_code", "groups", ["invite_code"], unique=True)
    op.create_unique_constraint("uq_groups_telegram_chat_id", "groups", ["telegram_chat_id"])

    # --- members ---
    op.create_table(
        "members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("groups.id"), nullable=False),
        sa.Column(
            "role",
            sa.Enum("ADMIN", "MEMBER", name="memberrole"),
            nullable=False,
            server_default="MEMBER",
        ),
        sa.Column("is_on_vacation", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("vacation_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("left_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_members_user_group", "members", ["user_id", "group_id"])

    # --- tasks ---
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("groups.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "schedule_type",
            sa.Enum(
                "DAILY", "EVERY_X_DAYS", "WEEKLY", "MONTHLY", "CUSTOM_CRON", name="scheduletype"
            ),
            nullable=False,
            server_default="DAILY",
        ),
        sa.Column("schedule_interval_days", sa.Integer(), nullable=True),
        sa.Column("schedule_cron", sa.String(length=128), nullable=True),
        sa.Column("reminder_interval_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("reminder_start_hour", sa.Integer(), nullable=False, server_default="8"),
        sa.Column("reminder_end_hour", sa.Integer(), nullable=False, server_default="22"),
        sa.Column("require_photo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- task_queue ---
    op.create_table(
        "task_queue",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("member_id", sa.Integer(), sa.ForeignKey("members.id"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_task_queue_task_id", "task_queue", ["task_id"])

    # --- task_assignments ---
    op.create_table(
        "task_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("member_id", sa.Integer(), sa.ForeignKey("members.id"), nullable=False),
        sa.Column("assigned_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "IN_PROGRESS", "COMPLETED", "OVERDUE", name="taskstatus"),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completion_duration_seconds", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- task_completion ---
    op.create_table(
        "task_completion",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "assignment_id", sa.Integer(), sa.ForeignKey("task_assignments.id"), nullable=False
        ),
        sa.Column("member_id", sa.Integer(), sa.ForeignKey("members.id"), nullable=False),
        sa.Column("photo_path", sa.String(length=512), nullable=True),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- penalties ---
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

    # --- audit_logs ---
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("groups.id"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- notification_templates ---
    op.create_table(
        "notification_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("groups.id"), nullable=False),
        sa.Column("template_type", sa.String(length=64), nullable=False),
        sa.Column("text_template", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=8), nullable=False, server_default="uz"),
    )


def downgrade() -> None:
    op.drop_table("notification_templates")
    op.drop_table("audit_logs")
    op.drop_table("penalties")
    op.drop_table("task_completion")
    op.drop_table("task_assignments")
    op.drop_table("task_queue")
    op.drop_table("tasks")
    op.drop_table("members")
    op.drop_table("groups")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS memberrole")
    op.execute("DROP TYPE IF EXISTS scheduletype")
    op.execute("DROP TYPE IF EXISTS taskstatus")
