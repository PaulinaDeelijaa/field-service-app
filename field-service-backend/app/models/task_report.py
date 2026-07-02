from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.photo import Photo
    from app.models.task import Task
    from app.models.user import User


class TaskReport(Base):
    """
    Work completion report submitted by a field worker.

    A single task can have multiple reports (e.g., partial progress + final).
    The mobile app writes to local SQLite; the sync engine upserts on client_id.

    materials_used is a JSONB array:
        [{"name": "Valve A", "quantity": 2, "unit": "pcs"}, ...]

    Keeping it as JSONB avoids a separate materials table while still allowing
    indexing via GIN and querying with jsonb_array_elements.  If material
    tracking grows complex, promote to a normalised table.
    """

    __tablename__ = "task_reports"

    __table_args__ = (
        UniqueConstraint("client_id", name="uq_task_reports_client_id"),
        Index("ix_task_reports_task_worker", "task_id", "worker_id"),
        Index("ix_task_reports_updated", "updated_at"),
    )

    # ── Identity ──────────────────────────────────────────────────────────────
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="Device-generated UUID; idempotency key for sync upserts.",
    )

    # ── Foreign keys ──────────────────────────────────────────────────────────
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    worker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # ── Content ───────────────────────────────────────────────────────────────
    content: Mapped[str] = mapped_column(Text, nullable=False)

    materials_used: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment='[{"name": "...", "quantity": 1, "unit": "pcs"}]',
    )

    time_spent_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Optimistic concurrency ────────────────────────────────────────────────
    server_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    task: Mapped["Task"] = relationship(
        "Task",
        back_populates="reports",
        lazy="noload",
    )

    worker: Mapped["User"] = relationship(
        "User",
        back_populates="reports",
        lazy="noload",
    )

    photos: Mapped[list["Photo"]] = relationship(
        "Photo",
        back_populates="report",
        cascade="all, delete-orphan",
        lazy="noload",
    )
