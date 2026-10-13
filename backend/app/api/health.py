# backend/app/api/health.py
"""Health check endpoints."""
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    version: str
    environment: str
    timestamp: datetime
    database: str
    details: dict[str, Any] | None = None


class DetailedHealthResponse(HealthResponse):
    """Detailed health check with system info."""
    uptime_seconds: float
    checks: dict[str, bool]


_start_time = datetime.now(UTC)


@router.get("/healthz", response_model=HealthResponse, summary="Basic health check")
async def health_check(
    session: AsyncSession = Depends(get_session),
) -> HealthResponse:
    """Basic health check endpoint for load balancers."""
    settings = get_settings()
    db_status = "unknown"

    try:
        await session.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        version=settings.app_version,
        environment=settings.environment,
        timestamp=datetime.now(UTC),
        database=db_status,
        details={"checks": {"database": db_status == "connected"}},
    )


@router.get("/health", response_model=DetailedHealthResponse, summary="Detailed health check")
async def detailed_health_check(
    session: AsyncSession = Depends(get_session),
) -> DetailedHealthResponse:
    """Detailed health check with system information."""
    settings = get_settings()
    now = datetime.now(UTC)
    uptime = (now - _start_time).total_seconds()

    db_status = "unknown"
    db_check = False

    try:
        await session.execute(text("SELECT 1"))
        db_status = "connected"
        db_check = True
    except Exception:
        db_status = "disconnected"

    checks = {
        "database": db_check,
        "config_loaded": True,
    }

    return DetailedHealthResponse(
        status="healthy" if all(checks.values()) else "degraded",
        version=settings.app_version,
        environment=settings.environment,
        timestamp=now,
        database=db_status,
        uptime_seconds=uptime,
        checks=checks,
        details={
            "checks": checks,
            "uptime_seconds": uptime,
            "database_status": db_status,
        },
    )