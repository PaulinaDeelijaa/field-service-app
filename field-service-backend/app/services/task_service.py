from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus
from app.models.user import User, UserRole
from app.schemas.task import TaskCreate, TaskUpdate


class TaskService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Read ──────────────────────────────────────────────────────────────────

    async def get_by_id(self, task_id: uuid.UUID, current_user: User) -> Task:
        task = await self.db.get(Task, task_id)
        if task is None or task.deleted_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
        self._assert_can_read(task, current_user)
        return task

    async def list_tasks(
        self,
        current_user: User,
        page: int = 1,
        page_size: int = 50,
        task_status: TaskStatus | None = None,
    ) -> tuple[list[Task], int]:
        query = select(Task).where(Task.deleted_at.is_(None))

        # Field workers see only their assigned tasks.
        if current_user.role == UserRole.FIELD_WORKER:
            query = query.where(Task.assigned_to_id == current_user.id)

        if task_status is not None:
            query = query.where(Task.status == task_status)

        count_query = select(func.count()).select_from(query.subquery())
        total: int = (await self.db.execute(count_query)).scalar_one()

        query = (
            query.order_by(Task.scheduled_at.asc().nulls_last(), Task.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = (await self.db.execute(query)).scalars().all()
        return list(rows), total

    # ── Write ─────────────────────────────────────────────────────────────────

    async def create(self, body: TaskCreate, current_user: User) -> Task:
        if current_user.role != UserRole.MANAGER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only managers can create tasks via the dashboard API.",
            )

        # Idempotency: if a task with this client_id already exists, return it.
        existing = await self._get_by_client_id(body.client_id)
        if existing is not None:
            return existing

        if body.assigned_to_id is not None:
            await self._assert_assignee_is_field_worker(body.assigned_to_id)

        task = Task(
            client_id=body.client_id,
            title=body.title,
            description=body.description,
            priority=body.priority,
            assigned_to_id=body.assigned_to_id,
            created_by_id=current_user.id,
            location_lat=body.location_lat,
            location_lng=body.location_lng,
            location_address=body.location_address,
            scheduled_at=body.scheduled_at,
        )
        self.db.add(task)
        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def update(
        self, task_id: uuid.UUID, body: TaskUpdate, current_user: User
    ) -> Task:
        task = await self.get_by_id(task_id, current_user)

        # Optimistic concurrency guard.
        if task.server_version != body.expected_version:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Version conflict: expected {body.expected_version}, "
                    f"server is at {task.server_version}. Fetch the latest version and retry."
                ),
            )

        self._assert_can_write(task, current_user)

        if body.assigned_to_id is not None:
            await self._assert_assignee_is_field_worker(body.assigned_to_id)

        # Apply only the fields the role is allowed to change.
        if current_user.role == UserRole.MANAGER:
            if body.title is not None:
                task.title = body.title
            if body.description is not None:
                task.description = body.description
            if body.priority is not None:
                task.priority = body.priority
            if body.assigned_to_id is not None:
                task.assigned_to_id = body.assigned_to_id
            if body.location_lat is not None:
                task.location_lat = body.location_lat
            if body.location_lng is not None:
                task.location_lng = body.location_lng
            if body.location_address is not None:
                task.location_address = body.location_address
            if body.scheduled_at is not None:
                task.scheduled_at = body.scheduled_at

        # Status transitions are allowed for both roles.
        if body.status is not None:
            self._validate_status_transition(task.status, body.status, current_user)
            task.status = body.status

        if body.started_at is not None:
            task.started_at = body.started_at
        if body.completed_at is not None:
            task.completed_at = body.completed_at

        task.server_version += 1
        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def soft_delete(self, task_id: uuid.UUID, current_user: User) -> None:
        if current_user.role != UserRole.MANAGER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only managers can delete tasks.",
            )
        task = await self.get_by_id(task_id, current_user)
        task.deleted_at = datetime.now(tz=timezone.utc)
        task.server_version += 1
        await self.db.flush()

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _get_by_client_id(self, client_id: uuid.UUID) -> Task | None:
        result = await self.db.execute(
            select(Task).where(Task.client_id == client_id)
        )
        return result.scalar_one_or_none()

    async def _assert_assignee_is_field_worker(self, user_id: uuid.UUID) -> None:
        assignee = await self.db.get(User, user_id)
        if assignee is None or not assignee.is_active:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Assignee not found or inactive.",
            )
        if assignee.role != UserRole.FIELD_WORKER:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Tasks can only be assigned to users with the field_worker role.",
            )

    def _assert_can_read(self, task: Task, user: User) -> None:
        if user.role == UserRole.MANAGER:
            return
        if task.assigned_to_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this task.",
            )

    def _assert_can_write(self, task: Task, user: User) -> None:
        if user.role == UserRole.MANAGER:
            return
        if task.assigned_to_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update tasks assigned to you.",
            )

    # Status machine: defines which transitions are legal per role.
    _ALLOWED_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
        TaskStatus.PENDING: {TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED},
        TaskStatus.IN_PROGRESS: {TaskStatus.COMPLETED, TaskStatus.CANCELLED},
        TaskStatus.COMPLETED: set(),
        TaskStatus.CANCELLED: set(),
    }

    def _validate_status_transition(
        self, current: TaskStatus, target: TaskStatus, user: User
    ) -> None:
        # Managers can force any transition for operational reasons.
        if user.role == UserRole.MANAGER:
            return
        if target not in self._ALLOWED_TRANSITIONS.get(current, set()):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status transition: {current} → {target}.",
            )
