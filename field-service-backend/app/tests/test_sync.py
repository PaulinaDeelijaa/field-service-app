from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus
from app.models.task_report import TaskReport
from app.models.user import UserRole
from app.tests.conftest import auth_headers, make_task, make_user

pytestmark = pytest.mark.asyncio

NOW = datetime.now(tz=timezone.utc)
PAST = NOW - timedelta(hours=2)
FUTURE = NOW + timedelta(hours=2)


def _sync_payload(**overrides) -> dict:
    base = {
        "device_id": "test-device-001",
        "last_synced_at": None,
        "tasks": [],
        "reports": [],
        "photos": [],
    }
    base.update(overrides)
    return base


class TestFirstSync:
    async def test_first_sync_returns_all_assigned_tasks(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        manager = await make_user(db, role=UserRole.MANAGER)
        worker = await make_user(db, role=UserRole.FIELD_WORKER)
        task1 = await make_task(db, creator=manager, assignee=worker)
        task2 = await make_task(db, creator=manager, assignee=worker)
        unrelated = await make_task(db, creator=manager)  # not assigned to worker

        response = await client.post(
            "/sync", json=_sync_payload(), headers=auth_headers(worker)
        )
        assert response.status_code == 200
        body = response.json()
        returned_ids = {t["id"] for t in body["tasks"]}

        assert str(task1.id) in returned_ids
        assert str(task2.id) in returned_ids
        assert str(unrelated.id) not in returned_ids

    async def test_first_sync_returns_server_timestamp(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        worker = await make_user(db, role=UserRole.FIELD_WORKER)
        response = await client.post(
            "/sync", json=_sync_payload(), headers=auth_headers(worker)
        )
        assert response.status_code == 200
        ts = response.json()["server_timestamp"]
        assert ts is not None
        parsed = datetime.fromisoformat(ts)
        assert abs((parsed - NOW).total_seconds()) < 5


class TestDeltaSync:
    async def test_delta_only_returns_records_newer_than_watermark(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        manager = await make_user(db, role=UserRole.MANAGER)
        worker = await make_user(db, role=UserRole.FIELD_WORKER)

        # Task created before the watermark — should NOT appear in delta.
        old_task = await make_task(db, creator=manager, assignee=worker)

        watermark = datetime.now(tz=timezone.utc)

        # Task created after the watermark — should appear in delta.
        new_task = await make_task(db, creator=manager, assignee=worker)

        response = await client.post(
            "/sync",
            json=_sync_payload(last_synced_at=watermark.isoformat()),
            headers=auth_headers(worker),
        )
        body = response.json()
        returned_ids = {t["id"] for t in body["tasks"]}

        assert str(new_task.id) in returned_ids
        assert str(old_task.id) not in returned_ids


class TestInboundTaskUpsert:
    async def test_new_task_from_client_is_persisted(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        worker = await make_user(db, role=UserRole.FIELD_WORKER)
        client_id = str(uuid.uuid4())

        response = await client.post(
            "/sync",
            json=_sync_payload(
                tasks=[
                    {
                        "client_id": client_id,
                        "title": "Offline-created task",
                        "status": "pending",
                        "priority": "medium",
                        "client_updated_at": NOW.isoformat(),
                        "client_version": 0,
                    }
                ]
            ),
            headers=auth_headers(worker),
        )
        assert response.status_code == 200

        result = await db.execute(
            select(Task).where(Task.client_id == uuid.UUID(client_id))
        )
        task = result.scalar_one_or_none()
        assert task is not None
        assert task.title == "Offline-created task"

    async def test_sync_is_idempotent(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        worker = await make_user(db, role=UserRole.FIELD_WORKER)
        client_id = str(uuid.uuid4())
        payload = _sync_payload(
            tasks=[
                {
                    "client_id": client_id,
                    "title": "Idempotent",
                    "status": "pending",
                    "priority": "low",
                    "client_updated_at": NOW.isoformat(),
                    "client_version": 0,
                }
            ]
        )
        await client.post("/sync", json=payload, headers=auth_headers(worker))
        await client.post("/sync", json=payload, headers=auth_headers(worker))

        result = await db.execute(
            select(Task).where(Task.client_id == uuid.UUID(client_id))
        )
        tasks = result.scalars().all()
        assert len(tasks) == 1  # exactly one row, not two


class TestConflictResolution:
    async def test_latest_timestamp_server_wins_when_server_is_newer(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        manager = await make_user(db, role=UserRole.MANAGER)
        worker = await make_user(db, role=UserRole.FIELD_WORKER)
        task = await make_task(db, creator=manager, assignee=worker)

        # Client sends an update with a timestamp OLDER than server's updated_at.
        stale_client_ts = (task.updated_at - timedelta(minutes=10)).isoformat()

        response = await client.post(
            "/sync",
            json=_sync_payload(
                tasks=[
                    {
                        "client_id": str(task.client_id),
                        "title": "Stale client title",
                        "status": "in_progress",
                        "priority": "low",
                        "client_updated_at": stale_client_ts,
                        "client_version": 0,
                    }
                ]
            ),
            headers=auth_headers(worker),
        )
        assert response.status_code == 200
        body = response.json()

        # The server should have rejected the client's stale change.
        conflicts = body["conflicts"]
        assert len(conflicts) == 1
        assert conflicts[0]["resolution"] in (
            "latest_timestamp_server",
            "server_wins",
        )

        # The task's title must remain unchanged.
        await db.refresh(task)
        assert task.title == "Test Task"

    async def test_latest_timestamp_client_wins_when_client_is_newer(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        manager = await make_user(db, role=UserRole.MANAGER)
        worker = await make_user(db, role=UserRole.FIELD_WORKER)
        task = await make_task(db, creator=manager, assignee=worker)

        fresh_client_ts = (task.updated_at + timedelta(minutes=10)).isoformat()

        response = await client.post(
            "/sync",
            json=_sync_payload(
                tasks=[
                    {
                        "client_id": str(task.client_id),
                        "title": "Fresh client title",
                        "status": "in_progress",
                        "priority": "medium",
                        "client_updated_at": fresh_client_ts,
                        "client_version": 1,
                    }
                ]
            ),
            headers=auth_headers(worker),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["conflicts"] == []

        await db.refresh(task)
        # Status should be updated (workers can update status).
        assert task.status == TaskStatus.IN_PROGRESS


class TestInboundReportUpsert:
    async def test_report_with_known_task_client_id_is_persisted(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        manager = await make_user(db, role=UserRole.MANAGER)
        worker = await make_user(db, role=UserRole.FIELD_WORKER)
        task = await make_task(db, creator=manager, assignee=worker)

        report_client_id = str(uuid.uuid4())
        response = await client.post(
            "/sync",
            json=_sync_payload(
                reports=[
                    {
                        "client_id": report_client_id,
                        "task_client_id": str(task.client_id),
                        "content": "Job done. Used 2 valves.",
                        "time_spent_minutes": 45,
                        "client_updated_at": NOW.isoformat(),
                        "client_version": 0,
                    }
                ]
            ),
            headers=auth_headers(worker),
        )
        assert response.status_code == 200

        result = await db.execute(
            select(TaskReport).where(
                TaskReport.client_id == uuid.UUID(report_client_id)
            )
        )
        report = result.scalar_one_or_none()
        assert report is not None
        assert report.task_id == task.id
        assert report.time_spent_minutes == 45

    async def test_report_with_unknown_task_client_id_is_skipped(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        worker = await make_user(db, role=UserRole.FIELD_WORKER)
        report_client_id = str(uuid.uuid4())
        unknown_task_client_id = str(uuid.uuid4())

        response = await client.post(
            "/sync",
            json=_sync_payload(
                reports=[
                    {
                        "client_id": report_client_id,
                        "task_client_id": unknown_task_client_id,
                        "content": "Orphan report",
                        "client_updated_at": NOW.isoformat(),
                        "client_version": 0,
                    }
                ]
            ),
            headers=auth_headers(worker),
        )
        assert response.status_code == 200  # No error — graceful skip.

        result = await db.execute(
            select(TaskReport).where(
                TaskReport.client_id == uuid.UUID(report_client_id)
            )
        )
        assert result.scalar_one_or_none() is None


class TestSyncLog:
    async def test_sync_log_is_written_on_success(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        from app.models.sync_log import SyncLog, SyncStatus

        worker = await make_user(db, role=UserRole.FIELD_WORKER)
        await client.post(
            "/sync",
            json=_sync_payload(device_id="log-test-device"),
            headers=auth_headers(worker),
        )

        result = await db.execute(
            select(SyncLog).where(SyncLog.device_id == "log-test-device")
        )
        log = result.scalar_one_or_none()
        assert log is not None
        assert log.status == SyncStatus.SUCCESS
        assert log.user_id == worker.id

    async def test_sync_with_conflicts_logs_partial_status(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        from app.models.sync_log import SyncLog, SyncStatus

        manager = await make_user(db, role=UserRole.MANAGER)
        worker = await make_user(db, role=UserRole.FIELD_WORKER)
        task = await make_task(db, creator=manager, assignee=worker)

        stale_ts = (task.updated_at - timedelta(minutes=5)).isoformat()
        device_id = f"partial-device-{uuid.uuid4().hex[:6]}"

        await client.post(
            "/sync",
            json=_sync_payload(
                device_id=device_id,
                tasks=[
                    {
                        "client_id": str(task.client_id),
                        "title": "Stale",
                        "status": "pending",
                        "priority": "low",
                        "client_updated_at": stale_ts,
                        "client_version": 0,
                    }
                ],
            ),
            headers=auth_headers(worker),
        )

        result = await db.execute(
            select(SyncLog).where(SyncLog.device_id == device_id)
        )
        log = result.scalar_one_or_none()
        assert log is not None
        assert log.status == SyncStatus.PARTIAL
