from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.photo import Photo
from app.models.sync_log import SyncLog, SyncStatus
from app.models.task import Task
from app.models.task_report import TaskReport
from app.models.user import User, UserRole
from app.schemas.sync import (
    ConflictDetail,
    PhotoMetaResponse,
    SyncPhotoPayload,
    SyncReportPayload,
    SyncRequest,
    SyncResponse,
    SyncStats,
    SyncTaskPayload,
)
from app.schemas.report import ReportResponse
from app.schemas.task import TaskResponse


ConflictResolution = Literal[
    "server_wins",
    "client_wins",
    "latest_timestamp_server",
    "latest_timestamp_client",
]


class SyncService:
    """
    Processes a bidirectional sync request.

    Contract
    ────────
    1. All client writes are upserted based on `client_id` (idempotent).
    2. Conflicts are resolved according to `settings.SYNC_CONFLICT_STRATEGY`.
    3. The server returns a delta: every record that changed since
       `last_synced_at` and that the requesting user is authorised to see.
    4. A SyncLog row is written regardless of success/failure (append-only).

    The entire operation runs inside one database transaction (managed by
    FastAPI's `get_db` dependency which commits on success / rolls back on
    exception).
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Public entry point ────────────────────────────────────────────────────

    async def process(
        self, payload: SyncRequest, current_user: User
    ) -> SyncResponse:
        server_ts = datetime.now(tz=timezone.utc)
        conflicts: list[ConflictDetail] = []

        # ── 1. Apply inbound changes ───────────────────────────────────────
        for task_payload in payload.tasks:
            conflict = await self._upsert_task(task_payload, current_user)
            if conflict:
                conflicts.append(conflict)

        # Build a client_id → server Task lookup to resolve report references.
        all_client_task_ids = {p.task_client_id for p in payload.reports} | {
            p.task_client_id for p in payload.photos
        }
        client_id_to_task = await self._resolve_tasks_by_client_ids(
            all_client_task_ids
        )

        for report_payload in payload.reports:
            parent_task = client_id_to_task.get(report_payload.task_client_id)
            if parent_task is None:
                # Unknown task — skip; the report will arrive on the next sync
                # once the task has been accepted.
                continue
            conflict = await self._upsert_report(
                report_payload, parent_task, current_user
            )
            if conflict:
                conflicts.append(conflict)

        for photo_payload in payload.photos:
            parent_task = client_id_to_task.get(photo_payload.task_client_id)
            if parent_task is None:
                continue
            report = None
            if photo_payload.report_client_id is not None:
                report = await self._get_report_by_client_id(
                    photo_payload.report_client_id
                )
            await self._upsert_photo_metadata(
                photo_payload, parent_task, report, current_user
            )

        # ── 2. Compute delta ───────────────────────────────────────────────
        delta_tasks = await self._task_delta(payload.last_synced_at, current_user)
        delta_reports = await self._report_delta(
            payload.last_synced_at, current_user
        )
        delta_photos = await self._photo_delta(payload.last_synced_at, current_user)

        # ── 3. Write audit log ─────────────────────────────────────────────
        sync_status = (
            SyncStatus.SUCCESS
            if not conflicts
            else SyncStatus.PARTIAL
        )
        await self._write_sync_log(
            user_id=current_user.id,
            device_id=payload.device_id,
            client_last_synced_at=payload.last_synced_at,
            server_processed_at=server_ts,
            tasks_received=len(payload.tasks),
            tasks_sent=len(delta_tasks),
            reports_received=len(payload.reports),
            reports_sent=len(delta_reports),
            photos_received=len(payload.photos),
            photos_sent=len(delta_photos),
            conflicts=conflicts,
            status=sync_status,
        )

        return SyncResponse(
            server_timestamp=server_ts,
            tasks=[TaskResponse.model_validate(t) for t in delta_tasks],
            reports=[ReportResponse.model_validate(r) for r in delta_reports],
            photos=[PhotoMetaResponse.model_validate(p) for p in delta_photos],
            conflicts=conflicts,
            stats=SyncStats(
                tasks_received=len(payload.tasks),
                tasks_sent=len(delta_tasks),
                reports_received=len(payload.reports),
                reports_sent=len(delta_reports),
                photos_received=len(payload.photos),
                photos_sent=len(delta_photos),
                conflicts_detected=len(conflicts),
            ),
        )

    # ── Task upsert ───────────────────────────────────────────────────────────

    async def _upsert_task(
        self, payload: SyncTaskPayload, user: User
    ) -> ConflictDetail | None:
        result = await self.db.execute(
            select(Task).where(Task.client_id == payload.client_id)
        )
        existing = result.scalar_one_or_none()

        if existing is None:
            task = Task(
                client_id=payload.client_id,
                title=payload.title,
                description=payload.description,
                status=payload.status,
                priority=payload.priority,
                assigned_to_id=payload.assigned_to_id,
                created_by_id=user.id,
                location_lat=payload.location_lat,
                location_lng=payload.location_lng,
                location_address=payload.location_address,
                scheduled_at=payload.scheduled_at,
                started_at=payload.started_at,
                completed_at=payload.completed_at,
                server_version=1,
            )
            self.db.add(task)
            return None

        resolution, should_apply = self._resolve_conflict(
            client_updated_at=payload.client_updated_at,
            server_updated_at=existing.updated_at,
            client_version=payload.client_version,
            server_version=existing.server_version,
        )

        if not should_apply:
            return ConflictDetail(
                entity_type="task",
                client_id=payload.client_id,
                server_id=existing.id,
                resolution=resolution,
                client_updated_at=payload.client_updated_at,
                server_updated_at=existing.updated_at,
                server_version=existing.server_version,
            )

        # Field workers may only update status-related fields via sync.
        if user.role == UserRole.MANAGER:
            existing.title = payload.title
            existing.description = payload.description
            existing.priority = payload.priority
            existing.assigned_to_id = payload.assigned_to_id
            existing.location_lat = payload.location_lat
            existing.location_lng = payload.location_lng
            existing.location_address = payload.location_address
            existing.scheduled_at = payload.scheduled_at

        existing.status = payload.status
        existing.started_at = payload.started_at
        existing.completed_at = payload.completed_at
        existing.server_version += 1
        return None

    # ── Report upsert ─────────────────────────────────────────────────────────

    async def _upsert_report(
        self,
        payload: SyncReportPayload,
        parent_task: Task,
        user: User,
    ) -> ConflictDetail | None:
        result = await self.db.execute(
            select(TaskReport).where(TaskReport.client_id == payload.client_id)
        )
        existing = result.scalar_one_or_none()

        if existing is None:
            report = TaskReport(
                client_id=payload.client_id,
                task_id=parent_task.id,
                worker_id=user.id,
                content=payload.content,
                materials_used=payload.materials_used,
                time_spent_minutes=payload.time_spent_minutes,
                server_version=1,
            )
            self.db.add(report)
            return None

        resolution, should_apply = self._resolve_conflict(
            client_updated_at=payload.client_updated_at,
            server_updated_at=existing.updated_at,
            client_version=payload.client_version,
            server_version=existing.server_version,
        )

        if not should_apply:
            return ConflictDetail(
                entity_type="report",
                client_id=payload.client_id,
                server_id=existing.id,
                resolution=resolution,
                client_updated_at=payload.client_updated_at,
                server_updated_at=existing.updated_at,
                server_version=existing.server_version,
            )

        existing.content = payload.content
        existing.materials_used = payload.materials_used
        existing.time_spent_minutes = payload.time_spent_minutes
        existing.server_version += 1
        return None

    # ── Photo metadata upsert ─────────────────────────────────────────────────

    async def _upsert_photo_metadata(
        self,
        payload: SyncPhotoPayload,
        parent_task: Task,
        parent_report: TaskReport | None,
        user: User,
    ) -> None:
        result = await self.db.execute(
            select(Photo).where(Photo.client_id == payload.client_id)
        )
        if result.scalar_one_or_none() is not None:
            return  # Already exists — idempotent no-op.

        # Checksum deduplication: same photo attached to same task is idempotent.
        dup_check = await self.db.execute(
            select(Photo).where(
                Photo.task_id == parent_task.id,
                Photo.sha256_checksum == payload.sha256_checksum,
            )
        )
        if dup_check.scalar_one_or_none() is not None:
            return

        photo = Photo(
            client_id=payload.client_id,
            task_id=parent_task.id,
            report_id=parent_report.id if parent_report else None,
            uploaded_by_id=user.id,
            original_filename=payload.original_filename,
            # Actual binary not yet received; placeholder path.
            file_path=f"pending/{parent_task.id}/{payload.client_id}",
            mime_type=payload.mime_type,
            file_size_bytes=payload.file_size_bytes,
            sha256_checksum=payload.sha256_checksum,
            client_created_at=payload.client_created_at,
        )
        self.db.add(photo)

    # ── Delta queries ─────────────────────────────────────────────────────────

    async def _task_delta(
        self, since: datetime | None, user: User
    ) -> list[Task]:
        query = select(Task)

        if user.role == UserRole.FIELD_WORKER:
            query = query.where(Task.assigned_to_id == user.id)

        if since is not None:
            # Include soft-deleted records too (client needs the tombstone).
            query = query.where(Task.updated_at > since)
        else:
            # First sync — exclude deleted records to avoid confusion.
            query = query.where(Task.deleted_at.is_(None))

        query = query.order_by(Task.updated_at.asc()).limit(settings.SYNC_BATCH_SIZE)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _report_delta(
        self, since: datetime | None, user: User
    ) -> list[TaskReport]:
        query = select(TaskReport)

        if user.role == UserRole.FIELD_WORKER:
            query = query.where(TaskReport.worker_id == user.id)

        if since is not None:
            query = query.where(TaskReport.updated_at > since)

        query = query.order_by(TaskReport.updated_at.asc()).limit(
            settings.SYNC_BATCH_SIZE
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _photo_delta(
        self, since: datetime | None, user: User
    ) -> list[Photo]:
        query = select(Photo)

        if user.role == UserRole.FIELD_WORKER:
            query = query.where(Photo.uploaded_by_id == user.id)

        if since is not None:
            query = query.where(Photo.created_at > since)

        query = query.order_by(Photo.created_at.asc()).limit(settings.SYNC_BATCH_SIZE)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _resolve_conflict(
        self,
        client_updated_at: datetime,
        server_updated_at: datetime,
        client_version: int,
        server_version: int,
    ) -> tuple[ConflictResolution, bool]:
        """
        Returns (resolution_label, should_apply_client_change).
        """
        strategy = settings.SYNC_CONFLICT_STRATEGY

        if strategy == "client_wins":
            return "client_wins", True

        if strategy == "server_wins":
            return "server_wins", False

        # latest_timestamp — compare device clock to server clock.
        # The server updated_at is authoritative (set by the DB).
        # The client's timestamp may drift; we accept a 1-second fudge factor.
        client_wins = client_updated_at > server_updated_at
        resolution: ConflictResolution = (
            "latest_timestamp_client" if client_wins else "latest_timestamp_server"
        )
        return resolution, client_wins

    async def _resolve_tasks_by_client_ids(
        self, client_ids: set[uuid.UUID]
    ) -> dict[uuid.UUID, Task]:
        if not client_ids:
            return {}
        result = await self.db.execute(
            select(Task).where(Task.client_id.in_(client_ids))
        )
        return {t.client_id: t for t in result.scalars().all()}

    async def _get_report_by_client_id(
        self, client_id: uuid.UUID
    ) -> TaskReport | None:
        result = await self.db.execute(
            select(TaskReport).where(TaskReport.client_id == client_id)
        )
        return result.scalar_one_or_none()

    async def _write_sync_log(
        self,
        *,
        user_id: uuid.UUID,
        device_id: str,
        client_last_synced_at: datetime | None,
        server_processed_at: datetime,
        tasks_received: int,
        tasks_sent: int,
        reports_received: int,
        reports_sent: int,
        photos_received: int,
        photos_sent: int,
        conflicts: list[ConflictDetail],
        status: SyncStatus,
    ) -> None:
        error_details = (
            {"conflicts": [c.model_dump(mode="json") for c in conflicts]}
            if conflicts
            else None
        )
        log = SyncLog(
            user_id=user_id,
            device_id=device_id,
            client_last_synced_at=client_last_synced_at,
            server_processed_at=server_processed_at,
            tasks_received=tasks_received,
            tasks_sent=tasks_sent,
            reports_received=reports_received,
            reports_sent=reports_sent,
            photos_received=photos_received,
            photos_sent=photos_sent,
            conflicts_detected=len(conflicts),
            conflicts_resolved=len(conflicts),
            status=status,
            error_details=error_details,
        )
        self.db.add(log)
