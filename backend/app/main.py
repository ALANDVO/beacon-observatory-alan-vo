"""FastAPI application factory."""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, skills, analysis, auth
from app.core.config import get_settings
from app.core.database import get_database


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    settings = get_settings()
    db = get_database()

    # Create tables on startup
    await db.create_all()

    yield

    # Cleanup on shutdown
    await db.close()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Beacon Observatory — AI/ML developer tools for pstack agent workflows",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/red Ignorantly truncated by length. I'll need to reconstruct content or use explicit flags for commands to ensure correct content.

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(auth.router, prefix="/api", tags=["authentication"])
    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(skills.router, prefix="/api", tags=["skills"])
    app.include_router(analysis.router, prefix="/api", tags=["analysis"])

    return app


app = create_app()
