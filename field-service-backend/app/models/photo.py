from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.task import Task
    from app.models.task_report import TaskReport
    from app.models.user import User


class Photo(Base):
    """
    Metadata record for a photo captured in the field.

    The binary content is stored on disk (or object storage); this table only
    holds the reference and enough metadata to support deduplication and sync.

    Deduplication strategy:
        The sha256_checksum column prevents the same photo from being uploaded
        multiple times across retries.  The sync endpoint checks whether a
        checksum already exists for the owning task before writing a file.

    client_created_at:
        Timestamp from the device at capture time, preserved separately from
        the server's created_at.  This is the canonical "when was the photo
        taken" field for display and audit.
    """

    __tablename__ = "photos"

    __table_args__ = (
        UniqueConstraint("client_id", name="uq_photos_client_id"),
        # Deduplication: one checksum per task (same photo retried = no-op)
        UniqueConstraint(
            "task_id", "sha256_checksum", name="uq_photos_task_checksum"
        ),
        Index("ix_photos_task_id", "task_id"),
        Index("ix_photos_report_id", "report_id"),
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
    )

    report_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("task_reports.id", ondelete="SET NULL"),
        nullable=True,
        comment="Nullable — photos can be attached to a task before a report is written.",
    )

    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # ── File metadata ─────────────────────────────────────────────────────────
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)

    # Relative path under UPLOAD_DIR, e.g. "tasks/<task_id>/<uuid>.jpg"
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)

    mime_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        server_default="image/jpeg",
    )

    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    sha256_checksum: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="SHA-256 hex digest of the raw file bytes.",
    )

    # ── Device capture time ───────────────────────────────────────────────────
    client_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Timestamp reported by the device at capture time.",
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    task: Mapped["Task"] = relationship(
        "Task",
        back_populates="photos",
        lazy="noload",
    )

    report: Mapped["TaskReport | None"] = relationship(
        "TaskReport",
        back_populates="photos",
        lazy="noload",
    )

    uploaded_by: Mapped["User"] = relationship(
        "User",
        lazy="noload",
    )
