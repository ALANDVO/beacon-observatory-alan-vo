# backend/app/models/skill.py
"""SQLAlchemy models for pstack skills, playbooks, and principles."""
from datetime import UTC, datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SkillType(PyEnum):
    """Types of pstack skills."""
    PLAYBOOK = "playbook"
    PRINCIPLE = "principle"
    SKILL = "skill"
    ROUTER = "router"


class AgentType(PyEnum):
    """Supported AI coding agents."""
    CLAUDE_CODE = "claude-code"
    CODEX = "codex"
    COPILOT = "copilot"
    PI = "pi"
    OPENCODE = "opencode"
    GEMINI = "gemini"
    PRIME_AGENT = "prime-agent"


class Skill(Base):
    """pstack skill/playbook/principle/registry entry."""

    __tablename__ = "skills"
    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_skill_name_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0.0")
    type: Mapped[SkillType] = mapped_column(Enum(SkillType), nullable=False, index=True)
    agent_type: Mapped[Optional[AgentType]] = mapped_column(Enum(AgentType), nullable=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    triggers: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array of trigger strings
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON for extensibility
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    generated_configs: Mapped[list["GeneratedConfig"]] = relationship(
        "GeneratedConfig", back_populates="skill", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Skill(id={self.id}, name='{self.name}', type={self.type.value}, agent_type={self.agent_type.value if self.agent_type else None})>"


class GeneratedConfig(Base):
    """Generated agent configuration from skills."""

    __tablename__ = "generated_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_type: Mapped[AgentType] = mapped_column(Enum(AgentType), nullable=False, index=True)
    config_content: Mapped[str] = mapped_column(Text, nullable=False)
    config_format: Mapped[str] = mapped_column(String(50), nullable=False, default="json")  # json, yaml, toml
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    # Relationships
    skill: Mapped["Skill"] = relationship("Skill", back_populates="generated_configs")

    def __repr__(self) -> str:
        return f"<GeneratedConfig(id={self.id}, skill_id={self.skill_id}, agent_type={self.agent_type.value})>"