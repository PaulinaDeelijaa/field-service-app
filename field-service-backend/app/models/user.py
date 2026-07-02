from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import pg_enum

if TYPE_CHECKING:
    from app.models.task import Task
    from app.models.task_report import TaskReport


class UserRole(str, enum.Enum):
    MANAGER = "manager"
    FIELD_WORKER = "field_worker"


class User(Base):
    """
    Central identity record.

    Role drives all authorization decisions — there is no separate permissions
    table; the two roles (MANAGER, FIELD_WORKER) cover every access pattern in
    this domain cleanly.  A junction table approach would be over-engineering
    here and would complicate sync logic.
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(254),
        unique=True,
        index=True,
        nullable=False,
    )

    hashed_password: Mapped[str] = mapped_column(String(128), nullable=False)

    full_name: Mapped[str] = mapped_column(String(120), nullable=False)

    role: Mapped[UserRole] = mapped_column(
        pg_enum(UserRole, name="user_role"),
        nullable=False,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    # back_populates keeps both sides in sync without loading extra data.
    assigned_tasks: Mapped[list["Task"]] = relationship(
        "Task",
        back_populates="assignee",
        foreign_keys="Task.assigned_to_id",
        lazy="noload",
    )

    created_tasks: Mapped[list["Task"]] = relationship(
        "Task",
        back_populates="creator",
        foreign_keys="Task.created_by_id",
        lazy="noload",
    )

    reports: Mapped[list["TaskReport"]] = relationship(
        "TaskReport",
        back_populates="worker",
        lazy="noload",
    )
