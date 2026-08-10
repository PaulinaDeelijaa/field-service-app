from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_manager
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserListResponse

router = APIRouter()


@router.get(
    "",
    response_model=list[UserListResponse],
    summary="List users (manager only)",
    dependencies=[Depends(require_manager())],
)
async def list_users(
    role: UserRole | None = Query(default=None, description="Filter by role"),
    db: AsyncSession = Depends(get_db),
) -> list[UserListResponse]:
    query = select(User).where(User.is_active.is_(True)).order_by(User.full_name.asc())
    if role is not None:
        query = query.where(User.role == role)

    result = await db.execute(query)
    return [UserListResponse.model_validate(u) for u in result.scalars().all()]
