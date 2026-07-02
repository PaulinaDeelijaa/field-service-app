from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import TaskStatus
from app.models.user import UserRole
from app.tests.conftest import auth_headers, make_task, make_user

pytestmark = pytest.mark.asyncio


class TestCreateTask:
    async def test_manager_creates_task(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        manager = await make_user(db, role=UserRole.MANAGER)
        worker = await make_user(db, role=UserRole.FIELD_WORKER)

        response = await client.post(
            "/tasks",
            json={
                "client_id": str(uuid.uuid4()),
                "title": "Inspect boiler room",
                "priority": "high",
                "assigned_to_id": str(worker.id),
            },
            headers=auth_headers(manager),
        )
        assert response.status_code == 201
        body = response.json()
        assert body["title"] == "Inspect boiler room"
        assert body["status"] == "pending"
        assert body["server_version"] == 1

    async def test_field_worker_cannot_create_task(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        worker = await make_user(db, role=UserRole.FIELD_WORKER)
        response = await client.post(
            "/tasks",
            json={"client_id": str(uuid.uuid4()), "title": "Sneaky task"},
            headers=auth_headers(worker),
        )
        assert response.status_code == 403

    async def test_create_task_is_idempotent(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        manager = await make_user(db, role=UserRole.MANAGER)
        client_id = str(uuid.uuid4())
        payload = {"client_id": client_id, "title": "Idempotent task"}

        r1 = await client.post("/tasks", json=payload, headers=auth_headers(manager))
        r2 = await client.post("/tasks", json=payload, headers=auth_headers(manager))

        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r1.json()["id"] == r2.json()["id"]

    async def test_cannot_assign_to_manager(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        manager = await make_user(db, role=UserRole.MANAGER)
        another_manager = await make_user(db, role=UserRole.MANAGER)
        response = await client.post(
            "/tasks",
            json={
                "client_id": str(uuid.uuid4()),
                "title": "Bad assignment",
                "assigned_to_id": str(another_manager.id),
            },
            headers=auth_headers(manager),
        )
        assert response.status_code == 422


class TestListTasks:
    async def test_manager_sees_all_tasks(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        manager = await make_user(db, role=UserRole.MANAGER)
        worker1 = await make_user(db, role=UserRole.FIELD_WORKER)
        worker2 = await make_user(db, role=UserRole.FIELD_WORKER)
        await make_task(db, creator=manager, assignee=worker1)
        await make_task(db, creator=manager, assignee=worker2)

        response = await client.get("/tasks", headers=auth_headers(manager))
        assert response.status_code == 200
        assert response.json()["total"] >= 2

    async def test_worker_sees_only_assigned_tasks(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        manager = await make_user(db, role=UserRole.MANAGER)
        worker = await make_user(db, role=UserRole.FIELD_WORKER)
        other_worker = await make_user(db, role=UserRole.FIELD_WORKER)

        await make_task(db, creator=manager, assignee=worker)
        await make_task(db, creator=manager, assignee=other_worker)

        response = await client.get("/tasks", headers=auth_headers(worker))
        assert response.status_code == 200
        data = response.json()
        for task in data["items"]:
            assert task["assigned_to_id"] == str(worker.id)


class TestUpdateTask:
    async def test_version_mismatch_returns_409(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        manager = await make_user(db, role=UserRole.MANAGER)
        task = await make_task(db, creator=manager, server_version=3)

        response = await client.patch(
            f"/tasks/{task.id}",
            json={"expected_version": 1, "title": "Stale update"},
            headers=auth_headers(manager),
        )
        assert response.status_code == 409

    async def test_worker_can_advance_status(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        manager = await make_user(db, role=UserRole.MANAGER)
        worker = await make_user(db, role=UserRole.FIELD_WORKER)
        task = await make_task(db, creator=manager, assignee=worker)

        response = await client.patch(
            f"/tasks/{task.id}",
            json={"expected_version": 1, "status": "in_progress"},
            headers=auth_headers(worker),
        )
        assert response.status_code == 200
        assert response.json()["status"] == "in_progress"
        assert response.json()["server_version"] == 2

    async def test_worker_cannot_skip_status(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        manager = await make_user(db, role=UserRole.MANAGER)
        worker = await make_user(db, role=UserRole.FIELD_WORKER)
        task = await make_task(db, creator=manager, assignee=worker)

        response = await client.patch(
            f"/tasks/{task.id}",
            json={"expected_version": 1, "status": "completed"},
            headers=auth_headers(worker),
        )
        assert response.status_code == 422

    async def test_worker_cannot_edit_title(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        manager = await make_user(db, role=UserRole.MANAGER)
        worker = await make_user(db, role=UserRole.FIELD_WORKER)
        task = await make_task(db, creator=manager, assignee=worker)

        original_title = task.title
        await client.patch(
            f"/tasks/{task.id}",
            json={"expected_version": 1, "title": "Worker override", "status": "in_progress"},
            headers=auth_headers(worker),
        )
        # Title should remain unchanged.
        get_resp = await client.get(f"/tasks/{task.id}", headers=auth_headers(manager))
        assert get_resp.json()["title"] == original_title


class TestDeleteTask:
    async def test_manager_can_soft_delete(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        manager = await make_user(db, role=UserRole.MANAGER)
        task = await make_task(db, creator=manager)

        response = await client.delete(
            f"/tasks/{task.id}", headers=auth_headers(manager)
        )
        assert response.status_code == 204

        get_resp = await client.get(
            f"/tasks/{task.id}", headers=auth_headers(manager)
        )
        assert get_resp.status_code == 404

    async def test_worker_cannot_delete(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        manager = await make_user(db, role=UserRole.MANAGER)
        worker = await make_user(db, role=UserRole.FIELD_WORKER)
        task = await make_task(db, creator=manager, assignee=worker)

        response = await client.delete(
            f"/tasks/{task.id}", headers=auth_headers(worker)
        )
        assert response.status_code == 403
