from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.photo import Photo
from app.models.task import Task
from app.models.user import User, UserRole
from app.schemas.sync import PhotoMetaResponse

router = APIRouter()


@router.get(
    "/task/{task_id}",
    response_model=list[PhotoMetaResponse],
    summary="List photos attached to a task",
)
async def list_task_photos(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PhotoMetaResponse]:
    task = await db.get(Task, task_id)
    if task is None or task.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Task not found.")

    if (
        current_user.role == UserRole.FIELD_WORKER
        and task.assigned_to_id != current_user.id
    ):
        raise HTTPException(status_code=403, detail="Access denied.")

    result = await db.execute(
        select(Photo)
        .where(Photo.task_id == task_id)
        .order_by(Photo.created_at.asc())
    )
    return [PhotoMetaResponse.model_validate(p) for p in result.scalars().all()]


@router.get(
    "/{photo_id}/file",
    summary="Download a photo file",
)
async def get_photo_file(
    photo_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    photo = await db.get(Photo, photo_id)
    if photo is None:
        raise HTTPException(status_code=404, detail="Photo not found.")

    task = await db.get(Task, photo.task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")

    if (
        current_user.role == UserRole.FIELD_WORKER
        and task.assigned_to_id != current_user.id
        and photo.uploaded_by_id != current_user.id
    ):
        raise HTTPException(status_code=403, detail="Access denied.")

    if photo.file_path.startswith("pending/"):
        raise HTTPException(status_code=404, detail="Photo file not uploaded yet.")

    absolute_path = Path(settings.UPLOAD_DIR) / photo.file_path
    if not absolute_path.is_file():
        raise HTTPException(status_code=404, detail="Photo file missing on server.")

    return FileResponse(
        path=absolute_path,
        media_type=photo.mime_type,
        filename=photo.original_filename,
    )
