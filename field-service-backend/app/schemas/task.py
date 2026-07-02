from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.models.task import TaskPriority, TaskStatus


class TaskCreate(BaseModel):
    """Used by managers via the web dashboard REST API."""

    client_id: uuid.UUID = Field(
        description="Client-generated UUID for idempotency. Re-use the same value on retry."
    )
    title: str = Field(min_length=3, max_length=255)
    description: str | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    assigned_to_id: uuid.UUID | None = None
    location_lat: float | None = Field(default=None, ge=-90, le=90)
    location_lng: float | None = Field(default=None, ge=-180, le=180)
    location_address: str | None = Field(default=None, max_length=512)
    scheduled_at: datetime | None = None


class TaskUpdate(BaseModel):
    """
    All fields optional — PATCH semantics.

    `expected_version` is mandatory to detect concurrent edits:
    the caller must echo the `server_version` it last saw.
    """

    title: str | None = Field(default=None, min_length=3, max_length=255)
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    assigned_to_id: uuid.UUID | None = None
    location_lat: float | None = Field(default=None, ge=-90, le=90)
    location_lng: float | None = Field(default=None, ge=-180, le=180)
    location_address: str | None = Field(default=None, max_length=512)
    scheduled_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    expected_version: Annotated[int, Field(ge=1)] = Field(
        description="Must match the current server_version — prevents lost updates."
    )


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    assigned_to_id: uuid.UUID | None
    created_by_id: uuid.UUID
    location_lat: float | None
    location_lng: float | None
    location_address: str | None
    scheduled_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    deleted_at: datetime | None
    server_version: int
    created_at: datetime
    updated_at: datetime


class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    total: int
    page: int
    page_size: int
