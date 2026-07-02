from __future__ import annotations

from enum import StrEnum
from functools import wraps
from typing import Callable

from fastapi import Depends, HTTPException, status

from app.core.dependencies import get_current_user
from app.models.user import User


class Role(StrEnum):
    MANAGER = "manager"
    FIELD_WORKER = "field_worker"


# Roles allowed to perform manager-only operations
MANAGER_ROLES: frozenset[str] = frozenset({Role.MANAGER})
ALL_ROLES: frozenset[str] = frozenset({Role.MANAGER, Role.FIELD_WORKER})


def require_roles(*roles: Role) -> Callable:
    """
    FastAPI dependency factory.

    Usage:
        @router.get("/tasks", dependencies=[Depends(require_roles(Role.MANAGER))])
    """
    allowed = frozenset(roles)

    async def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for this operation.",
            )
        return current_user

    return _check


def require_manager() -> Callable:
    return require_roles(Role.MANAGER)


def require_any_role() -> Callable:
    return require_roles(Role.MANAGER, Role.FIELD_WORKER)
