# backend/app/api/skills.py
"""Skills API endpoints."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.skill import Skill, SkillType, AgentType, GeneratedConfig


router = APIRouter(prefix="/skills", tags=["skills"])


# Request/Response Models
class SkillBase(BaseModel):
    """Base skill model."""
    name: str = Field(..., min_length=1, max_length=255, description="Skill name")
    version: str = Field(default="1.0.0", max_length=50, description="Skill version")
    type: SkillType = Field(..., description="Skill type")
    agent_type: Optional[AgentType] = Field(default=None, description="Target agent type")
    description: Optional[str] = Field(default=None, description="Skill description")
    content: str = Field(..., min_length=1, description="Skill content (markdown/text)")
    triggers: Optional[str] = Field(default=None, description="JSON array of trigger strings")
    metadata_json: Optional[str] = Field(default=None, description="JSON metadata for extensibility")
    is_active: bool = Field(default=True, description="Whether skill is active")

    @field_validator("triggers", "metadata_json", mode="before")
    @classmethod
    def validate_json(cls, v):
        if v is None or v == "":
            return None
        if isinstance(v, str):
            return v
        import json
        return json.dumps(v)


class SkillCreate(SkillBase):
    """Skill creation request."""
    pass


class SkillUpdate(BaseModel):
    """Skill update request."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    version: Optional[str] = Field(default=None, max_length=50)
    type: Optional[SkillType] = None
    agent_type: Optional[AgentType] = None
    description: Optional[str] = None
    content: Optional[str] = Field(default=None, min_length=1)
    triggers: Optional[str] = None
    metadata_json: Optional[str] = None
    is_active: Optional[bool] = None


class SkillResponse(SkillBase):
    """Skill response model."""
    id: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class SkillListResponse(BaseModel):
    """Paginated skill list response."""
    items: list[SkillResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class GeneratedConfigResponse(BaseModel):
    """Generated config response."""
    id: int
    skill_id: int
    agent_type: AgentType
    config_content: str
    config_format: str
    created_at: str

    class Config:
        from_attributes = True


# Helper functions
def skill_to_response(skill: Skill) -> SkillResponse:
    """Convert Skill ORM to response model."""
    return SkillResponse(
        id=skill.id,
        name=skill.name,
        version=skill.version,
        type=skill.type,
        agent_type=skill.agent_type,
        description=skill.description,
        content=skill.content,
        triggers=skill.triggers,
        metadata_json=skill.metadata_json,
        is_active=skill.is_active,
        created_at=skill.created_at.isoformat(),
        updated_at=skill.updated_at.isoformat(),
    )


# Endpoints
@router.post("", response_model=SkillResponse, status_code=status.HTTP_201_CREATED)
async def create_skill(
    skill_data: SkillCreate,
    session: AsyncSession = Depends(get_session),
) -> SkillResponse:
    """Create a new skill."""
    # Check for duplicate name + version
    existing = await session.execute(
        select(Skill).where(Skill.name == skill_data.name, Skill.version == skill_data.version)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Skill '{skill_data.name}' version '{skill_data.version}' already exists",
        )

    skill = Skill(**skill_data.model_dump())
    session.add(skill)
    await session.commit()
    await session.refresh(skill)
    return skill_to_response(skill)


@router.get("", response_model=SkillListResponse)
async def list_skills(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    type: Optional[SkillType] = Query(default=None, description="Filter by skill type"),
    agent_type: Optional[AgentType] = Query(default=None, description="Filter by agent type"),
    is_active: Optional[bool] = Query(default=None, description="Filter by active status"),
    search: Optional[str] = Query(default=None, description="Search in name/description"),
    session: AsyncSession = Depends(get_session),
) -> SkillListResponse:
    """List skills with pagination and filtering."""
    query = select(Skill)
    count_query = select(func.count(Skill.id))

    if type:
        query = query.where(Skill.type == type)
        count_query = count_query.where(Skill.type == type)
    if agent_type:
        query = query.where(Skill.agent_type == agent_type)
        count_query = count_query.where(Skill.agent_type == agent_type)
    if is_active is not None:
        query = query.where(Skill.is_active == is_active)
        count_query = count_query.where(Skill.is_active == is_active)
    if search:
        search_term = f"%{search}%"
        query = query.where(Skill.name.ilike(search_term) | Skill.description.ilike(search_term))
        count_query = count_query.where(Skill.name.ilike(search_term) | Skill.description.ilike(search_term))

    # Get total count
    total_result = await session.execute(count_query)
    total = total_result.scalar_one()

    # Apply pagination
    query = query.order_by(Skill.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    skills = result.scalars().all()

    return SkillListResponse(
        items=[skill_to_response(s) for s in skills],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{skill_id}", response_model=SkillResponse)
async def get_skill(
    skill_id: int,
    session: AsyncSession = Depends(get_session),
) -> SkillResponse:
    """Get a skill by ID."""
    skill = await session.get(Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    return skill_to_response(skill)


@router.put("/{skill_id}", response_model=SkillResponse)
async def update_skill(
    skill_id: int,
    skill_data: SkillUpdate,
    session: AsyncSession = Depends(get_session),
) -> SkillResponse:
    """Update a skill."""
    skill = await session.get(Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")

    update_data = skill_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(skill, field, value)

    await session.commit()
    await session.refresh(skill)
    return skill_to_response(skill)


@router.delete("/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill(
    skill_id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a skill."""
    skill = await session.get(Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")

    await session.delete(skill)
    await session.commit()


@router.post("/{skill_id}/generate-config", response_model=GeneratedConfigResponse)
async def generate_config(
    skill_id: int,
    agent_type: AgentType = Query(..., description="Target agent type"),
    config_format: str = Query("json", pattern="^(json|yaml|toml)$"),
    session: AsyncSession = Depends(get_session),
) -> GeneratedConfigResponse:
    """Generate agent configuration for a skill."""
    skill = await session.get(Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")

    # Generate configuration based on skill and agent type
    config_content = _generate_agent_config(skill, agent_type, config_format)

    generated = GeneratedConfig(
        skill_id=skill_id,
        agent_type=agent_type,
        config_content=config_content,
        config_format=config_format,
    )
    session.add(generated)
    await session.commit()
    await session.refresh(generated)

    return GeneratedConfigResponse(
        id=generated.id,
        skill_id=generated.skill_id,
        agent_type=generated.agent_type,
        config_content=generated.config_content,
        config_format=generated.config_format,
        created_at=generated.created_at.isoformat(),
    )


def _generate_agent_config(skill: Skill, agent_type: AgentType, config_format: str) -> str:
    """Generate agent-specific configuration from skill."""
    import json

    base_config = {
        "skill_name": skill.name,
        "skill_version": skill.version,
        "skill_type": skill.type.value,
        "description": skill.description,
        "content": skill.content,
        "triggers": json.loads(skill.triggers) if skill.triggers else [],
        "metadata": json.loads(skill.metadata_json) if skill.metadata_json else {},
    }

    # Agent-specific configuration generation
    if agent_type == AgentType.CLAUDE_CODE:
        config = _generate_claude_config(base_config)
    elif agent_type == AgentType.CODEX:
        config = _generate_codex_config(base_config)
    elif agent_type == AgentType.COPILOT:
        config = _generate_copilot_config(base_config)
    else:
        config = base_config

    if config_format == "yaml":
        import yaml
        return yaml.dump(config, sort_keys=False)
    elif config_format == "toml":
        import tomli_w
        return tomli_w.dumps(config)
    return json.dumps(config, indent=2)


def _generate_claude_config(base: dict) -> dict:
    """Generate Claude Code configuration."""
    return {
        "hooks": {
            "SessionStart": [
                {
                    "matcher": "",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"echo 'Your FIRST tool call on any engineering task must be the Skill tool with pstack:poteto-mode'",
                        }
                    ],
                }
            ]
        },
        "skills": [base],
    }


def _generate_codex_config(base: dict) -> dict:
    """Generate Codex configuration."""
    return {
        "plugins": {
            "pstack": {
                "hooks": {
                    "SessionStart": [
                        {
                            "type": "command",
                            "command": f"echo 'Your FIRST tool call on any engineering task must be the Skill tool with pstack:poteto-mode'",
                        }
                    ]
                },
                "skills": [base],
            }
        },
    }


def _generate_copilot_config(base: dict) -> dict:
    """Generate GitHub Copilot configuration."""
    return {
        "extensions": ["pstack"],
        "pstack": {
            "skills": [base],
            "router": "pstack:poteto-mode",
        },
    }