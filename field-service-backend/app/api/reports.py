from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.photo import Photo
from app.models.task import Task
from app.models.task_report import TaskReport
from app.models.user import User, UserRole
from app.schemas.report import ReportCreate, ReportResponse, ReportUpdate
from app.schemas.sync import PhotoMetaResponse

router = APIRouter()

_ALLOWED_MIME = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "application/octet-stream",
}


def _resolve_mime(content_type: str | None, filename: str | None) -> str:
    if content_type and content_type in _ALLOWED_MIME and content_type != "application/octet-stream":
        return "image/jpeg" if content_type == "image/jpg" else content_type

    suffix = Path(filename or "photo.jpg").suffix.lower()
    if suffix == ".png":
        return "image/png"
    if suffix == ".webp":
        return "image/webp"
    return "image/jpeg"


# ── Reports ───────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a task completion report",
)
async def create_report(
    body: ReportCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReportResponse:
    # Idempotency
    existing = await db.execute(
        select(TaskReport).where(TaskReport.client_id == body.client_id)
    )
    if (report := existing.scalar_one_or_none()) is not None:
        return ReportResponse.model_validate(report)

    task = await db.get(Task, body.task_id)
    if task is None or task.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Task not found.")

    if (
        current_user.role == UserRole.FIELD_WORKER
        and task.assigned_to_id != current_user.id
    ):
        raise HTTPException(status_code=403, detail="Task not assigned to you.")

    report = TaskReport(
        client_id=body.client_id,
        task_id=body.task_id,
        worker_id=current_user.id,
        content=body.content,
        materials_used=(
            [m.model_dump() for m in body.materials_used]
            if body.materials_used
            else None
        ),
        time_spent_minutes=body.time_spent_minutes,
    )
    db.add(report)
    await db.flush()
    await db.refresh(report)
    return ReportResponse.model_validate(report)


@router.get(
    "",
    response_model=list[ReportResponse],
    summary="List reports (optionally filtered by task)",
)
async def list_reports(
    task_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ReportResponse]:
    query = select(TaskReport).order_by(TaskReport.created_at.desc())

    if task_id is not None:
        task = await db.get(Task, task_id)
        if task is None or task.deleted_at is not None:
            raise HTTPException(status_code=404, detail="Task not found.")
        query = query.where(TaskReport.task_id == task_id)

    if current_user.role == UserRole.FIELD_WORKER:
        query = query.where(TaskReport.worker_id == current_user.id)

    result = await db.execute(query)
    return [ReportResponse.model_validate(r) for r in result.scalars().all()]


@router.get(
    "/{report_id}",
    response_model=ReportResponse,
    summary="Fetch a single report",
)
async def get_report(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReportResponse:
    report = await db.get(TaskReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found.")

    if (
        current_user.role == UserRole.FIELD_WORKER
        and report.worker_id != current_user.id
    ):
        raise HTTPException(status_code=403, detail="Access denied.")

    return ReportResponse.model_validate(report)


@router.patch(
    "/{report_id}",
    response_model=ReportResponse,
    summary="Update a report (author or manager only)",
)
async def update_report(
    report_id: uuid.UUID,
    body: ReportUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReportResponse:
    report = await db.get(TaskReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found.")

    if (
        current_user.role == UserRole.FIELD_WORKER
        and report.worker_id != current_user.id
    ):
        raise HTTPException(status_code=403, detail="Access denied.")

    if report.server_version != body.expected_version:
        raise HTTPException(
            status_code=409,
            detail=f"Version conflict: expected {body.expected_version}, server is at {report.server_version}.",
        )

    if body.content is not None:
        report.content = body.content
    if body.materials_used is not None:
        report.materials_used = [m.model_dump() for m in body.materials_used]
    if body.time_spent_minutes is not None:
        report.time_spent_minutes = body.time_spent_minutes

    report.server_version += 1
    await db.flush()
    await db.refresh(report)
    return ReportResponse.model_validate(report)


# ── Photo upload ──────────────────────────────────────────────────────────────

@router.post(
    "/{report_id}/photos",
    response_model=PhotoMetaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a photo file and link it to a report",
)
async def upload_photo(
    report_id: uuid.UUID,
    file: UploadFile,
    client_photo_id: uuid.UUID = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PhotoMetaResponse:
    report = await db.get(TaskReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found.")

    if (
        current_user.role == UserRole.FIELD_WORKER
        and report.worker_id != current_user.id
    ):
        raise HTTPException(status_code=403, detail="Access denied.")

    allowed_types = _ALLOWED_MIME
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=422,
            detail="Unsupported image type. Allowed: JPEG, PNG, WebP.",
        )

    contents = await file.read()

    if len(contents) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE_MB} MB.",
        )

    checksum = hashlib.sha256(contents).hexdigest()
    resolved_mime = _resolve_mime(file.content_type, file.filename)

    # Deduplication: same checksum on same task → return existing record.
    dup = await db.execute(
        select(Photo).where(
            Photo.task_id == report.task_id,
            Photo.sha256_checksum == checksum,
        )
    )
    if (existing_photo := dup.scalar_one_or_none()) is not None:
        return PhotoMetaResponse.model_validate(existing_photo)

    # Persist the binary file.
    relative_path = f"tasks/{report.task_id}/{client_photo_id}{Path(file.filename or 'photo').suffix}"
    absolute_path = Path(settings.UPLOAD_DIR) / relative_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiofiles.open(absolute_path, "wb") as f:
        await f.write(contents)

    # Look up or create the Photo metadata record.
    existing_meta = await db.execute(
        select(Photo).where(Photo.client_id == client_photo_id)
    )
    photo = existing_meta.scalar_one_or_none()

    if photo is None:
        from datetime import datetime, timezone

        photo = Photo(
            client_id=client_photo_id,
            task_id=report.task_id,
            report_id=report_id,
            uploaded_by_id=current_user.id,
            original_filename=file.filename or "photo",
            file_path=relative_path,
            mime_type=resolved_mime,
            file_size_bytes=len(contents),
            sha256_checksum=checksum,
            client_created_at=datetime.now(tz=timezone.utc),
        )
        db.add(photo)
    else:
        # Sync already created the metadata record — fill in the real path.
        photo.file_path = relative_path
        photo.sha256_checksum = checksum

    await db.flush()
    await db.refresh(photo)
    return PhotoMetaResponse.model_validate(photo)
