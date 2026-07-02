from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import pg_enum


class SyncStatus(str, enum.Enum):
    SUCCESS = "success"
    PARTIAL = "partial"  # some records accepted, some rejected due to conflicts
    FAILED = "failed"


class SyncLog(Base):
    """
    Immutable audit record for every POST /sync call.

    Purposes:
    1. Debugging — reproduce exactly what a client sent and what the server
       returned at a given point in time.
    2. Observability — detect sync failure patterns per device or user.
    3. Idempotency guard — if a client re-sends the exact same payload (same
       device_id + client_last_synced_at), the service can short-circuit and
       return the cached server_payload from the previous log entry.

    This table is append-only; records are never updated after INSERT.
    Retention policy (e.g. 90 days) should be enforced by a scheduled job.
    """

    __tablename__ = "sync_logs"

    __table_args__ = (
        Index("ix_sync_logs_user_synced", "user_id", "client_last_synced_at"),
        Index("ix_sync_logs_device", "device_id"),
        Index("ix_sync_logs_status", "status"),
    )

    # ── Who & what device ─────────────────────────────────────────────────────
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Stable identifier the mobile app generates once and persists to secure
    # storage (e.g. device UUID or a generated app-install ID).
    device_id: Mapped[str] = mapped_column(String(128), nullable=False)

    # ── Timing ────────────────────────────────────────────────────────────────
    # The timestamp the client reported as its last successful sync watermark.
    client_last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Null for a first-time sync (client has no watermark).",
    )

    server_processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="UTC timestamp when the server completed processing.",
    )

    # ── Counters ──────────────────────────────────────────────────────────────
    tasks_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tasks_sent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reports_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reports_sent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    photos_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    photos_sent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conflicts_detected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conflicts_resolved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ── Outcome ───────────────────────────────────────────────────────────────
    status: Mapped[SyncStatus] = mapped_column(
        pg_enum(SyncStatus, name="sync_status"),
        nullable=False,
        index=True,
    )

    # Structured error details when status = FAILED or PARTIAL
    error_details: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    user = relationship("User", lazy="noload")
