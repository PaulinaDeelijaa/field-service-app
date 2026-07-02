"""Block until PostgreSQL accepts connections. Used by the Docker entrypoint."""

from __future__ import annotations

import asyncio
import os
import sys
import time

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def wait_for_database(max_attempts: int = 30, delay_seconds: float = 2.0) -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        sys.exit(1)

    for attempt in range(1, max_attempts + 1):
        engine = create_async_engine(database_url)
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            print("Database is ready.")
            return
        except Exception as exc:
            if attempt == max_attempts:
                print(f"Database not ready after {max_attempts} attempts: {exc}", file=sys.stderr)
                sys.exit(1)
            print(f"Waiting for database ({attempt}/{max_attempts})...")
            time.sleep(delay_seconds)
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(wait_for_database())
