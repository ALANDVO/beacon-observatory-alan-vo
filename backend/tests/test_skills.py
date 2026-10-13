# backend/tests/test_skills.py
"""Tests for skills API endpoints."""
import tempfile
import os
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession, AsyncEngine

from app.main import create_app
from app.models.skill import Skill, SkillType, AgentType, Base
from app.core.database import get_session


def create_test_engine() -> tuple[AsyncEngine, str]:
    """Create a fresh test engine with a unique database file."""
    fd, path = tempfile.mkstemp(suffix='.db', prefix='test_beacon_')
    os.close(fd)
    url = f"sqlite+aiosqlite:///{path}"
    engine = create_async_engine(url, echo=False, future=True)
    return engine, path


@pytest.fixture
async def test_engine():
    """Create a fresh test engine for each test."""
    engine, path = create_test_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()
        try:
            os.unlink(path)
        except Exception:
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
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    
    app.dependency_overrides[get_session] = override_get_session
    return app


@pytest.fixture
async def client(app):
    """Create async test client."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


class TestSkillsEndpoints:
    """Test skills CRUD endpoints."""

    @pytest.mark.asyncio
    async def test_create_skill(self, client: AsyncClient):
        """POST /api/skills creates a new skill."""
        skill_data = {
            "name": "test-skill",
            "version": "1.0.0",
            "type": "playbook",
            "agent_type": "claude-code",
            "description": "A test playbook",
            "content": "# Test Playbook\n\nDo something useful.",
            "triggers": '["test", "playbook"]',
            "metadata_json": '{"author": "test"}',
            "is_active": True,
        }

        response = await client.post("/api/skills", json=skill_data)
        assert response.status_code == 201

        data = response.json()
        assert data["name"] == "test-skill"
        assert data["version"] == "1.0.0"
        assert data["type"] == "playbook"
        assert data["agent_type"] == "claude-code"
        assert data["description"] == "A test playbook"
        assert data["content"] == "# Test Playbook\n\nDo something useful."
        assert data["triggers"] == '["test", "playbook"]'
        assert data["metadata_json"] == '{"author": "test"}'
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    @pytest.mark.asyncio
    async def test_create_skill_minimal(self, client: AsyncClient):
        """POST /api/skills works with minimal required fields."""
        skill_data = {
            "name": "minimal-skill",
            "type": "principle",
            "content": "Always test your code.",
        }

        response = await client.post("/api/skills", json=skill_data)
        assert response.status_code == 201

        data = response.json()
        assert data["name"] == "minimal-skill"
        assert data["version"] == "1.0.0"  # default
        assert data["type"] == "principle"
        assert data["agent_type"] is None
        assert data["is_active"] is True  # default

    @pytest.mark.asyncio
    async def test_create_skill_duplicate_conflict(self, client: AsyncClient):
        """POST /api/skills returns 409 for duplicate name+version."""
        skill_data = {
            "name": "duplicate-skill",
            "version": "1.0.0",
            "type": "skill",
            "content": "First version",
        }

        response1 = await client.post("/api/skills", json=skill_data)
        assert response1.status_code == 201

        response2 = await client.post("/api/skills", json=skill_data)
        assert response2.status_code == 409
        assert "already exists" in response2.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_skill_validation_error(self, client: AsyncClient):
        """POST /api/skills returns 422 for invalid data."""
        # Missing required field
        response = await client.post("/api/skills", json={"type": "playbook"})
        assert response.status_code == 422

        # Empty name
        response = await client.post("/api/skills", json={"name": "", "type": "playbook", "content": "test"})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_skills(self, client: AsyncClient):
        """GET /api/skills returns paginated list."""
        # Create test skills
        for i in range(3):
            await client.post("/api/skills", json={
                "name": f"skill-{i}",
                "type": "playbook",
                "content": f"Content {i}",
            })

        response = await client.get("/api/skills")
        assert response.status_code == 200

        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data
        assert data["total"] == 3
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert len(data["items"]) == 3

    @pytest.mark.asyncio
    async def test_list_skills_pagination(self, client: AsyncClient):
        """GET /api/skills respects pagination parameters."""
        for i in range(5):
            await client.post("/api/skills", json={
                "name": f"skill-{i}",
                "type": "playbook",
                "content": f"Content {i}",
            })

        response = await client.get("/api/skills?page=2&page_size=2")
        assert response.status_code == 200

        data = response.json()
        assert data["page"] == 2
        assert data["page_size"] == 2
        assert len(data["items"]) == 2
        assert data["total_pages"] == 3

    @pytest.mark.asyncio
    async def test_list_skills_filter_by_type(self, client: AsyncClient):
        """GET /api/skills filters by type."""
        await client.post("/api/skills", json={"name": "playbook-1", "type": "playbook", "content": "test"})
        await client.post("/api/skills", json={"name": "principle-1", "type": "principle", "content": "test"})

        response = await client.get("/api/skills?type=playbook")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["type"] == "playbook"

    @pytest.mark.asyncio
    async def test_list_skills_filter_by_agent_type(self, client: AsyncClient):
        """GET /api/skills filters by agent_type."""
        await client.post("/api/skills", json={"name": "claude-skill", "type": "skill", "agent_type": "claude-code", "content": "test"})
        await client.post("/api/skills", json={"name": "codex-skill", "type": "skill", "agent_type": "codex", "content": "test"})

        response = await client.get("/api/skills?agent_type=claude-code")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["agent_type"] == "claude-code"

    @pytest.mark.asyncio
    async def test_list_skills_search(self, client: AsyncClient):
        """GET /api/skills searches in name and description."""
        await client.post("/api/skills", json={"name": "test-playbook", "type": "playbook", "description": "A test playbook", "content": "test"})
        await client.post("/api/skills", json={"name": "other-skill", "type": "skill", "description": "Something else", "content": "test"})

        response = await client.get("/api/skills?search=test")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "test-playbook"

    @pytest.mark.asyncio
    async def test_get_skill(self, client: AsyncClient):
        """GET /api/skills/{id} returns skill detail."""
        create_resp = await client.post("/api/skills", json={
            "name": "get-skill",
            "type": "playbook",
            "content": "Test content",
        })
        skill_id = create_resp.json()["id"]

        response = await client.get(f"/api/skills/{skill_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == skill_id
        assert data["name"] == "get-skill"

    @pytest.mark.asyncio
    async def test_get_skill_not_found(self, client: AsyncClient):
        """GET /api/skills/{id} returns 404 for non-existent skill."""
        response = await client.get("/api/skills/99999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_skill(self, client: AsyncClient):
        """PUT /api/skills/{id} updates a skill."""
        create_resp = await client.post("/api/skills", json={
            "name": "update-skill",
            "type": "playbook",
            "content": "Original content",
        })
        skill_id = create_resp.json()["id"]

        response = await client.put(f"/api/skills/{skill_id}", json={
            "description": "Updated description",
            "content": "Updated content",
        })
        assert response.status_code == 200

        data = response.json()
        assert data["description"] == "Updated description"
        assert data["content"] == "Updated content"
        assert data["name"] == "update-skill"  # unchanged

    @pytest.mark.asyncio
    async def test_update_skill_not_found(self, client: AsyncClient):
        """PUT /api/skills/{id} returns 404 for non-existent skill."""
        response = await client.put("/api/skills/99999", json={"content": "test"})
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_skill(self, client: AsyncClient):
        """DELETE /api/skills/{id} deletes a skill."""
        create_resp = await client.post("/api/skills", json={
            "name": "delete-skill",
            "type": "playbook",
            "content": "To be deleted",
        })
        skill_id = create_resp.json()["id"]

        response = await client.delete(f"/api/skills/{skill_id}")
        assert response.status_code == 204

        # Verify deleted
        get_resp = await client.get(f"/api/skills/{skill_id}")
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_skill_not_found(self, client: AsyncClient):
        """DELETE /api/skills/{id} returns 404 for non-existent skill."""
        response = await client.delete("/api/skills/99999")
        assert response.status_code == 404


class TestSkillConfigGeneration:
    """Test skill config generation endpoints."""

    @pytest.mark.asyncio
    async def test_generate_claude_config(self, client: AsyncClient):
        """POST /api/skills/{id}/generate-config generates Claude config."""
        create_resp = await client.post("/api/skills", json={
            "name": "claude-config-skill",
            "type": "playbook",
            "agent_type": "claude-code",
            "content": "Test playbook for Claude",
            "triggers": '["claude", "test"]',
        })
        skill_id = create_resp.json()["id"]

        response = await client.post(f"/api/skills/{skill_id}/generate-config?agent_type=claude-code")
        assert response.status_code == 200

        data = response.json()
        assert data["skill_id"] == skill_id
        assert data["agent_type"] == "claude-code"
        assert data["config_format"] == "json"
        assert "hooks" in data["config_content"]
        assert "SessionStart" in data["config_content"]

    @pytest.mark.asyncio
    async def test_generate_codex_config(self, client: AsyncClient):
        """POST /api/skills/{id}/generate-config generates Codex config."""
        create_resp = await client.post("/api/skills", json={
            "name": "codex-config-skill",
            "type": "skill",
            "agent_type": "codex",
            "content": "Test skill for Codex",
        })
        skill_id = create_resp.json()["id"]

        response = await client.post(f"/api/skills/{skill_id}/generate-config?agent_type=codex")
        assert response.status_code == 200

        data = response.json()
        assert data["skill_id"] == skill_id
        assert data["agent_type"] == "codex"
        assert "plugins" in data["config_content"]

    @pytest.mark.asyncio
    async def test_generate_copilot_config(self, client: AsyncClient):
        """POST /api/skills/{id}/generate-config generates Copilot config."""
        create_resp = await client.post("/api/skills", json={
            "name": "copilot-config-skill",
            "type": "router",
            "agent_type": "copilot",
            "content": "Test router for Copilot",
        })
        skill_id = create_resp.json()["id"]

        response = await client.post(f"/api/skills/{skill_id}/generate-config?agent_type=copilot")
        assert response.status_code == 200

        data = response.json()
        assert data["skill_id"] == skill_id
        assert data["agent_type"] == "copilot"
        assert "extensions" in data["config_content"]

    @pytest.mark.asyncio
    async def test_generate_config_yaml_format(self, client: AsyncClient):
        """POST /api/skills/{id}/generate-config supports YAML format."""
        create_resp = await client.post("/api/skills", json={
            "name": "yaml-config-skill",
            "type": "playbook",
            "content": "Test",
        })
        skill_id = create_resp.json()["id"]

        response = await client.post(f"/api/skills/{skill_id}/generate-config?agent_type=claude-code&config_format=yaml")
        assert response.status_code == 200

        data = response.json()
        assert data["config_format"] == "yaml"
        assert "yaml-config-skill" in data["config_content"]

    @pytest.mark.asyncio
    async def test_generate_config_not_found(self, client: AsyncClient):
        """POST /api/skills/{id}/generate-config returns 404 for non-existent skill."""
        response = await client.post("/api/skills/99999/generate-config?agent_type=claude-code")
        assert response.status_code == 404