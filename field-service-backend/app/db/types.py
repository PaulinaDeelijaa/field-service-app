from __future__ import annotations

import enum

from sqlalchemy import Enum


def pg_enum(enum_class: type[enum.Enum], name: str) -> Enum:
    """
    PostgreSQL enum column that persists Python enum *values* (e.g. "manager"),
    not member names (e.g. "MANAGER").
    """
    return Enum(
        enum_class,
        name=name,
        create_constraint=True,
        values_callable=lambda members: [member.value for member in members],
    )
