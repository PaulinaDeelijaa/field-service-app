"""
Create the first manager account if none exists.

Usage (with Docker running):
    docker compose exec api python docker/seed_admin.py

Optional env vars:
    SEED_ADMIN_EMAIL     (default: admin@fieldservice.com)
    SEED_ADMIN_PASSWORD  (default: Admin1234)
    SEED_ADMIN_NAME      (default: System Admin)
"""

from __future__ import annotations

import asyncio
import os
import sys

# Ensure /app is on the path when run from the container working directory.
sys.path.insert(0, "/app")

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.user import User, UserRole


async def seed() -> None:
    email = os.getenv("SEED_ADMIN_EMAIL", "admin@fieldservice.com")
    password = os.getenv("SEED_ADMIN_PASSWORD", "Admin1234")
    full_name = os.getenv("SEED_ADMIN_NAME", "System Admin")

    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none() is not None:
            print(f"Admin already exists: {email}")
            return

        user = User(
            email=email,
            full_name=full_name,
            hashed_password=hash_password(password),
            role=UserRole.MANAGER,
        )
        db.add(user)
        await db.commit()
        print(f"Created manager account: {email}")


if __name__ == "__main__":
    asyncio.run(seed())
