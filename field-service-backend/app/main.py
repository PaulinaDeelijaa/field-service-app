from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.core.config import settings
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup: verify DB connectivity; the pool warms lazily.
    yield
    # Shutdown: drain connection pool cleanly.
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── Middleware ────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(o) for o in settings.CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Compress sync payloads — they can be large JSON blobs.
    app.add_middleware(GZipMiddleware, minimum_size=1024)

    # ── Routers ───────────────────────────────────────────────────────────────
    # Imported here to avoid circular imports at module load time.
    from app.api import auth, photos, reports, sync, tasks

    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
    app.include_router(reports.router, prefix="/reports", tags=["reports"])
    app.include_router(photos.router, prefix="/photos", tags=["photos"])
    app.include_router(sync.router, prefix="/sync", tags=["sync"])

    @app.get("/health", tags=["ops"])
    async def health_check() -> dict:
        return {"status": "ok", "version": settings.APP_VERSION}

    return app


app = create_app()
