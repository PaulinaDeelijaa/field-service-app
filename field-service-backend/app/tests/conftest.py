from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.user import User, UserRole

# ── Test database ─────────────────────────────────────────────────────────────
# Uses the real DATABASE_URL but a separate "_test" schema / database.
# Override DATABASE_URL in your environment for CI:
#   DATABASE_URL=postgresql+asyncpg://...@localhost/field_service_test

TEST_DATABASE_URL = settings.DATABASE_URL.replace(
    "/field_service", "/field_service_test"
)

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    """Single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    """Create all tables once per test session, drop on teardown."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """
    Wraps each test in a transaction that is rolled back on completion.
    This keeps tests isolated without truncating tables.
    """
    async with test_engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await conn.rollback()


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP test client wired to the test DB session."""

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ── Factories ─────────────────────────────────────────────────────────────────

async def make_user(
    db: AsyncSession,
    role: UserRole = UserRole.FIELD_WORKER,
    email: str | None = None,
) -> User:
    user = User(
        email=email or f"{uuid.uuid4().hex[:8]}@test.com",
        full_name="Test User",
        hashed_password=hash_password("Password1"),
        role=role,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def make_task(
    db: AsyncSession,
    creator: User,
    assignee: User | None = None,
    status: TaskStatus = TaskStatus.PENDING,
    server_version: int = 1,
) -> Task:
    task = Task(
        client_id=uuid.uuid4(),
        title="Test Task",
        description="A test task.",
        status=status,
        priority=TaskPriority.MEDIUM,
        assigned_to_id=assignee.id if assignee else None,
        created_by_id=creator.id,
        server_version=server_version,
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)
    return task


def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(user.id, user.role)
    return {"Authorization": f"Bearer {token}"}
