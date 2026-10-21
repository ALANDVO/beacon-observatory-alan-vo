# backend/tests/test_analysis.py
"""Tests for hook effectiveness analysis API endpoints."""
import tempfile
import os
import pytest
from datetime import UTC, datetime
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession, AsyncEngine

from app.main import create_app
from app.models.analysis import SessionLog, LogSource, SessionType, AnalysisJob, AnalysisStatus, Base
from app.core.database import get_session


def create_test_engine() -> tuple[AsyncEngine, str]:
    """Create a fresh test engine with a unique database file."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}", echo=False)
    return engine, path


@pytest.fixture
async def test_engine():
    """Create a fresh test engine for each test."""
    engine, path = create_test_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()
    try:
        os.unlink(path)
    except OSError:
        pass


@pytest.fixture
async def test_session_factory(test_engine):
    """Create session factory for test."""
    return async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
def app(test_session_factory):
    """Create test app with overridden database."""
    app = create_app()

    async def override_get_session():
        async with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    return app


@pytest.fixture
async def client(app):
    """Create async test client."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


class TestSessionLogEndpoints:
    """Test session log CRUD endpoints."""

    async def test_create_session_log(self, client):
        """Test creating a single session log."""
        payload = {
            "source": "claude-code",
            "session_id": "test-session-1",
            "session_type": "main",
            "timestamp": "2024-01-15T10:00:00Z",
            "hook_present": True,
            "router_opened": True,
            "playbook_opened": False,
            "principle_opened": False,
            "metadata_json": '{"agent_version": "1.0"}',
        }
        response = await client.post("/api/analyze/logs", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["source"] == "claude-code"
        assert data["session_id"] == "test-session-1"
        assert data["session_type"] == "main"
        assert data["hook_present"] is True
        assert data["router_opened"] is True
        assert data["playbook_opened"] is False
        assert data["principle_opened"] is False
        assert "id" in data
        assert "created_at" in data

    async def test_create_session_log_minimal(self, client):
        """Test creating a session log with only required fields."""
        payload = {
            "source": "codex",
            "session_id": "test-session-2",
            "session_type": "headless",
            "timestamp": "2024-01-15T11:00:00Z",
        }
        response = await client.post("/api/analyze/logs", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["source"] == "codex"
        assert data["session_type"] == "headless"
        assert data["hook_present"] is False
        assert data["router_opened"] is False
        assert data["playbook_opened"] is False
        assert data["principle_opened"] is False

    async def test_create_session_logs_bulk(self, client):
        """Test creating multiple session logs in bulk."""
        payload = [
            {
                "source": "claude-code",
                "session_id": "bulk-1",
                "session_type": "main",
                "timestamp": "2024-01-15T10:00:00Z",
                "hook_present": True,
                "router_opened": True,
            },
            {
                "source": "claude-code",
                "session_id": "bulk-2",
                "session_type": "subagent",
                "timestamp": "2024-01-15T10:05:00Z",
                "hook_present": True,
                "router_opened": False,
            },
            {
                "source": "codex",
                "session_id": "bulk-3",
                "session_type": "headless",
                "timestamp": "2024-01-15T10:10:00Z",
                "hook_present": True,
                "router_opened": True,
            },
        ]
        response = await client.post("/api/analyze/logs/bulk", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert len(data) == 3
        assert data[0]["session_id"] == "bulk-1"
        assert data[1]["session_id"] == "bulk-2"
        assert data[2]["session_id"] == "bulk-3"

    async def test_list_session_logs(self, client):
        """Test listing session logs with pagination."""
        # Create some logs first
        for i in range(5):
            await client.post("/api/analyze/logs", json={
                "source": "claude-code",
                "session_id": f"list-{i}",
                "session_type": "main",
                "timestamp": f"2024-01-15T10:{i:02d}:00Z",
            })

        response = await client.get("/api/analyze/logs?page=1&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert data["total"] == 5
        assert data["total_pages"] == 3
        assert len(data["items"]) == 2

    async def test_list_session_logs_filter_by_source(self, client):
        """Test filtering session logs by source."""
        await client.post("/api/analyze/logs", json={
            "source": "claude-code",
            "session_id": "filter-1",
            "session_type": "main",
            "timestamp": "2024-01-15T10:00:00Z",
        })
        await client.post("/api/analyze/logs", json={
            "source": "codex",
            "session_id": "filter-2",
            "session_type": "headless",
            "timestamp": "2024-01-15T10:00:00Z",
        })

        response = await client.get("/api/analyze/logs?source=claude-code")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["source"] == "claude-code"

    async def test_list_session_logs_filter_by_session_type(self, client):
        """Test filtering session logs by session type."""
        await client.post("/api/analyze/logs", json={
            "source": "claude-code",
            "session_id": "filter-type-1",
            "session_type": "main",
            "timestamp": "2024-01-15T10:00:00Z",
        })
        await client.post("/api/analyze/logs", json={
            "source": "claude-code",
            "session_id": "filter-type-2",
            "session_type": "subagent",
            "timestamp": "2024-01-15T10:00:00Z",
        })

        response = await client.get("/api/analyze/logs?session_type=subagent")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["session_type"] == "subagent"


class TestAnalysisJobEndpoints:
    """Test analysis job endpoints."""

    async def test_create_analysis_job(self, client):
        """Test creating an analysis job."""
        payload = {
            "name": "Test Analysis",
            "source_filter": "claude-code",
            "session_type_filter": "main",
        }
        response = await client.post("/api/analyze/jobs", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Analysis"
        assert data["source_filter"] == "claude-code"
        assert data["session_type_filter"] == "main"
        assert data["status"] == "pending"
        assert data["total_logs"] == 0
        assert "id" in data
        assert "created_at" in data

    async def test_create_analysis_job_minimal(self, client):
        """Test creating an analysis job with minimal fields."""
        payload = {"name": "Minimal Job"}
        response = await client.post("/api/analyze/jobs", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Minimal Job"
        assert data["source_filter"] is None
        assert data["session_type_filter"] is None
        assert data["status"] == "pending"

    async def test_list_analysis_jobs(self, client):
        """Test listing analysis jobs."""
        await client.post("/api/analyze/jobs", json={"name": "Job 1"})
        await client.post("/api/analyze/jobs", json={"name": "Job 2"})

        response = await client.get("/api/analyze/jobs")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    async def test_get_analysis_job(self, client):
        """Test getting a specific analysis job."""
        create_response = await client.post("/api/analyze/jobs", json={"name": "Get Job"})
        job_id = create_response.json()["id"]

        response = await client.get(f"/api/analyze/jobs/{job_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == job_id
        assert data["name"] == "Get Job"

    async def test_get_analysis_job_not_found(self, client):
        """Test getting a non-existent analysis job."""
        response = await client.get("/api/analyze/jobs/99999")
        assert response.status_code == 404

    async def test_run_analysis_job(self, client):
        """Test running an analysis job computes metrics."""
        # Create some session logs
        await client.post("/api/analyze/logs/bulk", json=[
            {
                "source": "claude-code",
                "session_id": "run-1",
                "session_type": "main",
                "timestamp": "2024-01-15T10:00:00Z",
                "hook_present": True,
                "router_opened": True,
                "playbook_opened": True,
                "principle_opened": False,
            },
            {
                "source": "claude-code",
                "session_id": "run-2",
                "session_type": "main",
                "timestamp": "2024-01-15T10:05:00Z",
                "hook_present": True,
                "router_opened": True,
                "playbook_opened": False,
                "principle_opened": True,
            },
            {
                "source": "claude-code",
                "session_id": "run-3",
                "session_type": "subagent",
                "timestamp": "2024-01-15T10:10:00Z",
                "hook_present": True,
                "router_opened": False,
                "playbook_opened": False,
                "principle_opened": False,
            },
            {
                "source": "codex",
                "session_id": "run-4",
                "session_type": "headless",
                "timestamp": "2024-01-15T10:15:00Z",
                "hook_present": True,
                "router_opened": True,
                "playbook_opened": True,
                "principle_opened": True,
            },
        ])

        # Create job
        create_response = await client.post("/api/analyze/jobs", json={
            "name": "Run Test",
        })
        job_id = create_response.json()["id"]

        # Run job
        response = await client.post(f"/api/analyze/jobs/{job_id}/run")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["total_logs"] == 4
        assert data["processed_logs"] == 4
        assert data["progress"] == 100.0
        assert data["result_json"] is not None

        # Verify results were created
        report_response = await client.get(f"/api/analyze/jobs/{job_id}/report")
        assert report_response.status_code == 200
        report = report_response.json()
        assert report["job"]["id"] == job_id
        assert report["summary"]["total_sessions_analyzed"] == 4
        assert "by_source" in report["summary"]
        assert "claude-code" in report["summary"]["by_source"]
        assert "codex" in report["summary"]["by_source"]

        claude_main = report["summary"]["by_source"]["claude-code"]["main"]
        assert claude_main["total_sessions"] == 2
        assert claude_main["hook_reach_rate"] == 100.0
        assert claude_main["router_open_rate"] == 100.0
        assert claude_main["playbook_open_rate"] == 50.0
        assert claude_main["principle_open_rate"] == 50.0
        # opens_per_100 = router_opens / hook_reach * 100 = 2/2 * 100 = 100
        assert claude_main["opens_per_100_prompts"] == 100.0

        claude_subagent = report["summary"]["by_source"]["claude-code"]["subagent"]
        assert claude_subagent["total_sessions"] == 1
        assert claude_subagent["hook_reach_rate"] == 100.0
        assert claude_subagent["router_open_rate"] == 0.0
        assert claude_subagent["opens_per_100_prompts"] == 0.0

        codex_headless = report["summary"]["by_source"]["codex"]["headless"]
        assert codex_headless["total_sessions"] == 1
        assert codex_headless["router_open_rate"] == 100.0
        assert codex_headless["opens_per_100_prompts"] == 100.0

    async def test_run_analysis_job_with_filters(self, client):
        """Test running an analysis job with source/type filters."""
        await client.post("/api/analyze/logs/bulk", json=[
            {
                "source": "claude-code",
                "session_id": "filter-run-1",
                "session_type": "main",
                "timestamp": "2024-01-15T10:00:00Z",
                "hook_present": True,
                "router_opened": True,
            },
            {
                "source": "codex",
                "session_id": "filter-run-2",
                "session_type": "headless",
                "timestamp": "2024-01-15T10:00:00Z",
                "hook_present": True,
                "router_opened": True,
            },
        ])

        create_response = await client.post("/api/analyze/jobs", json={
            "name": "Filtered Run",
            "source_filter": "claude-code",
        })
        job_id = create_response.json()["id"]

        response = await client.post(f"/api/analyze/jobs/{job_id}/run")
        assert response.status_code == 200
        data = response.json()
        assert data["total_logs"] == 1  # Only claude-code logs
        assert data["status"] == "completed"

        report_response = await client.get(f"/api/analyze/jobs/{job_id}/report")
        report = report_response.json()
        assert report["summary"]["total_sessions_analyzed"] == 1
        assert "claude-code" in report["summary"]["by_source"]
        assert "codex" not in report["summary"]["by_source"]

    async def test_run_analysis_job_already_running(self, client):
        """Test running a completed job is allowed (re-run)."""
        create_response = await client.post("/api/analyze/jobs", json={"name": "Running Job"})
        job_id = create_response.json()["id"]

        # First run
        await client.post(f"/api/analyze/jobs/{job_id}/run")

        # Second run should succeed (re-run allowed)
        response = await client.post(f"/api/analyze/jobs/{job_id}/run")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

    async def test_get_effectiveness_report_not_found(self, client):
        """Test getting report for non-existent job."""
        response = await client.get("/api/analyze/jobs/99999/report")
        assert response.status_code == 404

    async def test_get_effectiveness_report_not_completed(self, client):
        """Test getting report for incomplete job."""
        create_response = await client.post("/api/analyze/jobs", json={"name": "Pending Job"})
        job_id = create_response.json()["id"]

        response = await client.get(f"/api/analyze/jobs/{job_id}/report")
        assert response.status_code == 400

    async def test_delete_analysis_job(self, client):
        """Test deleting an analysis job."""
        create_response = await client.post("/api/analyze/jobs", json={"name": "Delete Me"})
        job_id = create_response.json()["id"]

        response = await client.delete(f"/api/analyze/jobs/{job_id}")
        assert response.status_code == 204

        # Verify it's gone
        get_response = await client.get(f"/api/analyze/jobs/{job_id}")
        assert get_response.status_code == 404

    async def test_delete_analysis_job_not_found(self, client):
        """Test deleting a non-existent job."""
        response = await client.delete("/api/analyze/jobs/99999")
        assert response.status_code == 404


class TestEffectivenessMetrics:
    """Test specific effectiveness metric calculations."""

    async def test_opens_per_100_calculation(self, client):
        """Test opens per 100 prompts calculation."""
        # 10 sessions, 8 have hook, 4 open router
        await client.post("/api/analyze/logs/bulk", json=[
            {
                "source": "claude-code",
                "session_id": f"calc-{i}",
                "session_type": "main",
                "timestamp": "2024-01-15T10:00:00Z",
                "hook_present": i < 8,
                "router_opened": i < 4,
            }
            for i in range(10)
        ])

        create_response = await client.post("/api/analyze/jobs", json={"name": "Calc Test"})
        job_id = create_response.json()["id"]
        await client.post(f"/api/analyze/jobs/{job_id}/run")

        report_response = await client.get(f"/api/analyze/jobs/{job_id}/report")
        report = report_response.json()
        main_data = report["summary"]["by_source"]["claude-code"]["main"]

        # hook_reach = 8/10 = 80%
        assert main_data["hook_reach_rate"] == 80.0
        # router_open_rate = 4/10 = 40%
        assert main_data["router_open_rate"] == 40.0
        # opens_per_100 = 4/8 * 100 = 50
        assert main_data["opens_per_100_prompts"] == 50.0

    async def test_zero_hook_reach_handling(self, client):
        """Test opens per 100 when hook_reach is zero."""
        await client.post("/api/analyze/logs/bulk", json=[
            {
                "source": "claude-code",
                "session_id": f"zero-{i}",
                "session_type": "main",
                "timestamp": "2024-01-15T10:00:00Z",
                "hook_present": False,
                "router_opened": False,
            }
            for i in range(5)
        ])

        create_response = await client.post("/api/analyze/jobs", json={"name": "Zero Test"})
        job_id = create_response.json()["id"]
        await client.post(f"/api/analyze/jobs/{job_id}/run")

        report_response = await client.get(f"/api/analyze/jobs/{job_id}/report")
        report = report_response.json()
        main_data = report["summary"]["by_source"]["claude-code"]["main"]

        assert main_data["hook_reach_rate"] == 0.0
        assert main_data["router_open_rate"] == 0.0
        assert main_data["opens_per_100_prompts"] == 0.0

    async def test_main_vs_subagent_comparison(self, client):
        """Test comparison between main and subagent sessions."""
        await client.post("/api/analyze/logs/bulk", json=[
            # Main sessions: high hook reach, high router opens
            *[{
                "source": "claude-code",
                "session_id": f"main-{i}",
                "session_type": "main",
                "timestamp": "2024-01-15T10:00:00Z",
                "hook_present": True,
                "router_opened": True,
            } for i in range(100)],
            # Subagent sessions: low hook reach, low router opens
            *[{
                "source": "claude-code",
                "session_id": f"sub-{i}",
                "session_type": "subagent",
                "timestamp": "2024-01-15T10:00:00Z",
                "hook_present": i < 3,  # Only 3% have hook
                "router_opened": i < 1,  # Only 1% open router
            } for i in range(100)],
        ])

        create_response = await client.post("/api/analyze/jobs", json={"name": "Compare Test"})
        job_id = create_response.json()["id"]
        await client.post(f"/api/analyze/jobs/{job_id}/run")

        report_response = await client.get(f"/api/analyze/jobs/{job_id}/report")
        report = report_response.json()
        by_source = report["summary"]["by_source"]["claude-code"]

        main_data = by_source["main"]
        subagent_data = by_source["subagent"]

        # Main: 100 sessions, all have hook, all open router
        assert main_data["total_sessions"] == 100
        assert main_data["hook_reach_rate"] == 100.0
        assert main_data["router_open_rate"] == 100.0
        assert main_data["opens_per_100_prompts"] == 100.0

        # Subagent: 100 sessions, 3 have hook, 1 opens router
        assert subagent_data["total_sessions"] == 100
        assert subagent_data["hook_reach_rate"] == 3.0
        assert subagent_data["router_open_rate"] == 1.0
        # opens_per_100 = 1/3 * 100 = 33.33...
        assert abs(subagent_data["opens_per_100_prompts"] - 33.33) < 0.1