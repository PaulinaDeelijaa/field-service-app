from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.sync import SyncRequest, SyncResponse
from app.services.sync_service import SyncService

router = APIRouter()


@router.post(
    "",
    response_model=SyncResponse,
    summary="Bidirectional data synchronisation",
    description="""
Upload all local changes (tasks, reports, photo metadata) that occurred since
`last_synced_at`, and receive all server-side changes the client has not yet
seen.

**Idempotency**: re-sending the same payload is safe — all writes use
`client_id` as the upsert key.

**Conflict resolution**: controlled by the server's `SYNC_CONFLICT_STRATEGY`
setting. Rejected changes are listed in the `conflicts` array of the response.

**Watermark**: store `server_timestamp` from the response and send it as
`last_synced_at` on the next request.
""",
)
async def sync(
    payload: SyncRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SyncResponse:
    service = SyncService(db)
    return await service.process(payload, current_user)
