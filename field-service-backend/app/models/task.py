from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import pg_enum

if TYPE_CHECKING:
    from app.models.photo import Photo
    from app.models.task_report import TaskReport
    from app.models.user import User


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Task(Base):
    """
    Core work unit that travels between the backend and mobile clients.

    Sync design decisions:
    ─────────────────────
    client_id
        A UUID the mobile device generates before it ever touches the server.
        This is the idempotency key for POST /sync — if a task arrives twice
        (network retry, duplicate sync), the upsert on client_id is a no-op.

    server_version
        An integer monotonic counter incremented on every server-side write.
        The sync engine compares (client_version, client_updated_at) against
        (server_version, updated_at) to determine which side wins a conflict.

    deleted_at (soft delete)
        Hard deletes break sync.  Tombstones let mobile clients know a record
        is gone without losing the audit trail.  The sync endpoint filters
        records WHERE deleted_at IS NULL for active data.
    """

    __tablename__ = "tasks"

    __table_args__ = (
        UniqueConstraint("client_id", name="uq_tasks_client_id"),
        # Fast lookups for the sync delta query:
        #   WHERE assigned_to_id = :uid AND updated_at > :last_synced_at
        Index("ix_tasks_assignee_updated", "assigned_to_id", "updated_at"),
        Index("ix_tasks_status", "status"),
    )

    # ── Identity ──────────────────────────────────────────────────────────────
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="Device-generated UUID; used as idempotency key during sync.",
    )

    # ── Content ───────────────────────────────────────────────────────────────
    title: Mapped[str] = mapped_column(String(255), nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Status & priority ─────────────────────────────────────────────────────
    status: Mapped[TaskStatus] = mapped_column(
        pg_enum(TaskStatus, name="task_status"),
        nullable=False,
        default=TaskStatus.PENDING,
        server_default="pending",
    )

    priority: Mapped[TaskPriority] = mapped_column(
        pg_enum(TaskPriority, name="task_priority"),
        nullable=False,
        default=TaskPriority.MEDIUM,
        server_default="medium",
    )

    # ── Ownership ─────────────────────────────────────────────────────────────
    assigned_to_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # ── Location ──────────────────────────────────────────────────────────────
    # Stored as plain floats rather than PostGIS geometry for simplicity.
    # Migrate to geometry(Point, 4326) if spatial queries become a requirement.
    location_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_address: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # ── Scheduling ────────────────────────────────────────────────────────────
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Soft delete ───────────────────────────────────────────────────────────
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    # ── Optimistic concurrency ────────────────────────────────────────────────
    # Incremented atomically by the sync service on every accepted write.
    # The mobile client echoes this value back so the server can detect
    # stale updates: UPDATE ... WHERE id = :id AND server_version = :expected_version.
    server_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    assignee: Mapped["User | None"] = relationship(
        "User",
        back_populates="assigned_tasks",
        foreign_keys=[assigned_to_id],
        lazy="noload",
    )

    creator: Mapped["User"] = relationship(
        "User",
        back_populates="created_tasks",
        foreign_keys=[created_by_id],
        lazy="noload",
    )

    reports: Mapped[list["TaskReport"]] = relationship(
        "TaskReport",
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    photos: Mapped[list["Photo"]] = relationship(
        "Photo",
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="noload",
    )
