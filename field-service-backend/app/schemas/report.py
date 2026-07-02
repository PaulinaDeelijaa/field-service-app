from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MaterialItem(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    quantity: float = Field(gt=0)
    unit: str = Field(min_length=1, max_length=32)


class ReportCreate(BaseModel):
    client_id: uuid.UUID = Field(
        description="Device-generated UUID; used as idempotency key on sync."
    )
    task_id: uuid.UUID
    content: str = Field(min_length=1)
    materials_used: list[MaterialItem] | None = None
    time_spent_minutes: int | None = Field(default=None, ge=0, le=1440)


class ReportUpdate(BaseModel):
    content: str | None = Field(default=None, min_length=1)
    materials_used: list[MaterialItem] | None = None
    time_spent_minutes: int | None = Field(default=None, ge=0, le=1440)
    expected_version: int = Field(ge=1)


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    task_id: uuid.UUID
    worker_id: uuid.UUID
    content: str
    materials_used: list[dict[str, Any]] | None
    time_spent_minutes: int | None
    server_version: int
    created_at: datetime
    updated_at: datetime
