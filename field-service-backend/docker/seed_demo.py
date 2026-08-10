"""
Seed demo data: one field worker and sample tasks.

Usage (with Docker running):
    docker compose exec api python docker/seed_demo.py
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "/app")

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.user import User, UserRole

WORKER_EMAIL = "worker@fieldservice.com"
WORKER_PASSWORD = "Worker1234"
WORKER_NAME = "Demo Field Worker"


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        manager = (
            await db.execute(select(User).where(User.role == UserRole.MANAGER))
        ).scalar_one_or_none()
        if manager is None:
            print("No manager found. Run seed_admin.py first.")
            return

        result = await db.execute(select(User).where(User.email == WORKER_EMAIL))
        worker = result.scalar_one_or_none()
        if worker is None:
            worker = User(
                email=WORKER_EMAIL,
                full_name=WORKER_NAME,
                hashed_password=hash_password(WORKER_PASSWORD),
                role=UserRole.FIELD_WORKER,
            )
            db.add(worker)
            await db.flush()
            print(f"Created worker: {WORKER_EMAIL} / {WORKER_PASSWORD}")
        else:
            print(f"Worker already exists: {WORKER_EMAIL}")

        demo_tasks = [
            {
                "title": "Inspect HVAC unit — Building A",
                "description": "Check filters, refrigerant levels, and thermostat calibration.",
                "priority": TaskPriority.HIGH,
                "status": TaskStatus.PENDING,
                "location_address": "Rruga Agim Ramadani 12, Prishtina",
            },
            {
                "title": "Replace faulty circuit breaker",
                "description": "Panel 3B — customer reported intermittent power loss.",
                "priority": TaskPriority.CRITICAL,
                "status": TaskStatus.IN_PROGRESS,
                "location_address": "Bulevardi Bill Clinton, Prishtina",
            },
            {
                "title": "Annual fire extinguisher check",
                "description": "Verify pressure gauges and replace expired units.",
                "priority": TaskPriority.MEDIUM,
                "status": TaskStatus.PENDING,
                "location_address": "Rruga Nëna Terezë 45, Prishtina",
            },
        ]

        scheduled = datetime.now(tz=timezone.utc) + timedelta(hours=2)
        created = 0

        for spec in demo_tasks:
            existing = await db.execute(
                select(Task).where(
                    Task.title == spec["title"],
                    Task.deleted_at.is_(None),
                )
            )
            if existing.scalar_one_or_none() is not None:
                continue

            task = Task(
                client_id=uuid.uuid4(),
                title=spec["title"],
                description=spec["description"],
                priority=spec["priority"],
                status=spec["status"],
                assigned_to_id=worker.id,
                created_by_id=manager.id,
                location_address=spec["location_address"],
                scheduled_at=scheduled,
                started_at=(
                    datetime.now(tz=timezone.utc)
                    if spec["status"] == TaskStatus.IN_PROGRESS
                    else None
                ),
            )
            db.add(task)
            created += 1
            scheduled += timedelta(hours=4)

        await db.commit()
        print(f"Created {created} demo task(s) assigned to {WORKER_EMAIL}")


if __name__ == "__main__":
    asyncio.run(seed())
