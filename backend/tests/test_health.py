# backend/tests/test_health.py
"""Tests for health check endpoints."""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture
def app():
    """Create test app."""
    return create_app()


@pytest.fixture
async def client(app):
    """Create async test client."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


class TestHealthEndpoints:
    """Test health check endpoints."""

    @pytest.mark.asyncio
    async def test_healthz_returns_healthy(self, client: AsyncClient):
        """GET /api/healthz returns 200 with healthy status."""
        response = await client.get("/api/healthz")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] in ("healthy", "degraded")
        assert "version" in data
        assert "environment" in data
        assert "timestamp" in data
        assert "database" in data

    @pytest.mark.asyncio
    async def test_healthz_response_schema(self, client: AsyncClient):
        """GET /api/healthz response matches expected schema."""
        response = await client.get("/api/healthz")
        assert response.status_code == 200

        data = response.json()
        required_fields = {"status", "version", "environment", "timestamp", "database"}
        assert set(data.keys()) >= required_fields
        assert isinstance(data["version"], str)
        assert isinstance(data["environment"], str)
        assert data["database"] in ("connected", "disconnected", "unknown")

    @pytest.mark.asyncio
    async def test_healthz_response_time_under_threshold(self, client: AsyncClient):
        """GET /api/healthz responds within acceptable time."""
        import time

        start = time.perf_counter()
        response = await client.get("/api/healthz")
        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        assert elapsed < 1.0  # Should respond within 1 second

    @pytest.mark.asyncio
    async def test_detailed_health_returns_checks(self, client: AsyncClient):
        """GET /api/health returns detailed checks."""
        response = await client.get("/api/health")
        assert response.status_code == 200

        data = response.json()
        assert "checks" in data
        assert isinstance(data["checks"], dict)
        assert "database" in data["checks"]
        assert "config_loaded" in data["checks"]
        assert "uptime_seconds" in data
        assert isinstance(data["uptime_seconds"], (int, float))
        assert data["uptime_seconds"] >= 0

    @pytest.mark.asyncio
    async def test_detailed_health_schema(self, client: AsyncClient):
        """GET /api/health response matches detailed schema."""
        response = await client.get("/api/health")
        assert response.status_code == 200

        data = response.json()
        required_fields = {
            "status",
            "version",
            "environment",
            "timestamp",
            "database",
            "uptime_seconds",
            "checks",
        }
        assert set(data.keys()) >= required_fields
        assert isinstance(data["checks"], dict)
        assert all(isinstance(v, bool) for v in data["checks"].values())