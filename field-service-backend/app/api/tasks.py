from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.task import TaskStatus
from app.models.user import User
from app.schemas.task import TaskCreate, TaskListResponse, TaskResponse, TaskUpdate
from app.services.task_service import TaskService

router = APIRouter()


def _service(db: AsyncSession = Depends(get_db)) -> TaskService:
    return TaskService(db)


@router.get(
    "",
    response_model=TaskListResponse,
    summary="List tasks (managers see all; workers see only assigned)",
)
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    task_status: TaskStatus | None = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
    service: TaskService = Depends(_service),
) -> TaskListResponse:
    items, total = await service.list_tasks(
        current_user=current_user,
        page=page,
        page_size=page_size,
        task_status=task_status,
    )
    return TaskListResponse(
        items=[TaskResponse.model_validate(t) for t in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task (manager only)",
)
async def create_task(
    body: TaskCreate,
    current_user: User = Depends(get_current_user),
    service: TaskService = Depends(_service),
) -> TaskResponse:
    task = await service.create(body, current_user)
    return TaskResponse.model_validate(task)


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Get a single task by ID",
)
async def get_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: TaskService = Depends(_service),
) -> TaskResponse:
    task = await service.get_by_id(task_id, current_user)
    return TaskResponse.model_validate(task)


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Partially update a task",
)
async def update_task(
    task_id: uuid.UUID,
    body: TaskUpdate,
    current_user: User = Depends(get_current_user),
    service: TaskService = Depends(_service),
) -> TaskResponse:
    task = await service.update(task_id, body, current_user)
    return TaskResponse.model_validate(task)


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Soft-delete a task (manager only)",
)
async def delete_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: TaskService = Depends(_service),
) -> None:
    await service.soft_delete(task_id, current_user)
