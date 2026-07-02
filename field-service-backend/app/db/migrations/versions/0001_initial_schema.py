"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-02

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enum types ────────────────────────────────────────────────────────────
    op.execute("CREATE TYPE user_role AS ENUM ('manager', 'field_worker')")
    op.execute(
        "CREATE TYPE task_status AS ENUM ('pending', 'in_progress', 'completed', 'cancelled')"
    )
    op.execute(
        "CREATE TYPE task_priority AS ENUM ('low', 'medium', 'high', 'critical')"
    )
    op.execute(
        "CREATE TYPE sync_status AS ENUM ('success', 'partial', 'failed')"
    )

    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("hashed_password", sa.String(128), nullable=False),
        sa.Column("full_name", sa.String(120), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM("manager", "field_worker", name="user_role", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"])

    # ── tasks ─────────────────────────────────────────────────────────────────
    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending", "in_progress", "completed", "cancelled",
                name="task_status", create_type=False,
            ),
            server_default="pending",
            nullable=False,
        ),
        sa.Column(
            "priority",
            postgresql.ENUM(
                "low", "medium", "high", "critical",
                name="task_priority", create_type=False,
            ),
            server_default="medium",
            nullable=False,
        ),
        sa.Column("assigned_to_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("location_lat", sa.Float(), nullable=True),
        sa.Column("location_lng", sa.Float(), nullable=True),
        sa.Column("location_address", sa.String(512), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "server_version",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["assigned_to_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id", name="uq_tasks_client_id"),
    )
    op.create_index("ix_tasks_id", "tasks", ["id"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_deleted_at", "tasks", ["deleted_at"])
    op.create_index(
        "ix_tasks_assignee_updated", "tasks", ["assigned_to_id", "updated_at"]
    )

    # ── task_reports ──────────────────────────────────────────────────────────
    op.create_table(
        "task_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("worker_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("materials_used", postgresql.JSONB(), nullable=True),
        sa.Column("time_spent_minutes", sa.Integer(), nullable=True),
        sa.Column(
            "server_version",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["worker_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id", name="uq_task_reports_client_id"),
    )
    op.create_index("ix_task_reports_id", "task_reports", ["id"])
    op.create_index(
        "ix_task_reports_task_worker", "task_reports", ["task_id", "worker_id"]
    )
    op.create_index("ix_task_reports_updated", "task_reports", ["updated_at"])

    # ── photos ────────────────────────────────────────────────────────────────
    op.create_table(
        "photos",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("uploaded_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("file_path", sa.String(512), nullable=False),
        sa.Column("mime_type", sa.String(64), server_default="image/jpeg", nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256_checksum", sa.String(64), nullable=False),
        sa.Column("client_created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["report_id"], ["task_reports.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id", name="uq_photos_client_id"),
        sa.UniqueConstraint(
            "task_id", "sha256_checksum", name="uq_photos_task_checksum"
        ),
    )
    op.create_index("ix_photos_id", "photos", ["id"])
    op.create_index("ix_photos_task_id", "photos", ["task_id"])
    op.create_index("ix_photos_report_id", "photos", ["report_id"])

    # ── sync_logs ─────────────────────────────────────────────────────────────
    op.create_table(
        "sync_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("device_id", sa.String(128), nullable=False),
        sa.Column("client_last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("server_processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tasks_received", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tasks_sent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reports_received", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reports_sent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("photos_received", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("photos_sent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "conflicts_detected", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "conflicts_resolved", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "success", "partial", "failed",
                name="sync_status", create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("error_details", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sync_logs_id", "sync_logs", ["id"])
    op.create_index("ix_sync_logs_device", "sync_logs", ["device_id"])
    op.create_index("ix_sync_logs_status", "sync_logs", ["status"])
    op.create_index(
        "ix_sync_logs_user_synced",
        "sync_logs",
        ["user_id", "client_last_synced_at"],
    )

    # ── updated_at trigger ────────────────────────────────────────────────────
    # SQLAlchemy's onupdate=func.now() sets the value at the ORM layer, but a
    # DB-level trigger guarantees updated_at is refreshed even for raw SQL
    # updates (Alembic data migrations, direct psql edits, bulk updates).
    op.execute("""
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    for table in ("users", "tasks", "task_reports", "photos", "sync_logs"):
        op.execute(f"""
            CREATE TRIGGER trg_{table}_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """)


def downgrade() -> None:
    for table in ("sync_logs", "photos", "task_reports", "tasks", "users"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_updated_at ON {table}")

    op.execute("DROP FUNCTION IF EXISTS set_updated_at()")

    op.drop_table("sync_logs")
    op.drop_table("photos")
    op.drop_table("task_reports")
    op.drop_table("tasks")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS sync_status")
    op.execute("DROP TYPE IF EXISTS task_priority")
    op.execute("DROP TYPE IF EXISTS task_status")
    op.execute("DROP TYPE IF EXISTS user_role")
