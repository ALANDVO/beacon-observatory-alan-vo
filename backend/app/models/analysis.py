# backend/app/models/analysis.py
"""SQLAlchemy models for hook effectiveness analysis."""
from datetime import UTC, datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class LogSource(PyEnum):
    """Source of session logs."""
    CLAUDE_CODE = "claude-code"
    CODEX = "codex"
    COPILOT = "copilot"
    PI = "pi"
    OPENCODE = "opencode"
    GEMINI = "gemini"
    PRIME_AGENT = "prime-agent"


class SessionType(PyEnum):
    """Type of session."""
    MAIN = "main"
    SUBAGENT = "subagent"
    HEADLESS = "headless"


class AnalysisStatus(PyEnum):
    """Status of analysis job."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SessionLog(Base):
    """Raw session log entry for analysis."""

    __tablename__ = "session_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[LogSource] = mapped_column(Enum(LogSource), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    session_type: Mapped[SessionType] = mapped_column(Enum(SessionType), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    hook_present: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)
    hook_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    router_opened: Mapped[bool] = mapped_column(default=False, nullable=False)
    playbook_opened: Mapped[bool] = mapped_column(default=False, nullable=False)
    principle_opened: Mapped[bool] = mapped_column(default=False, nullable=False)
    agent_type_detail: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    raw_log_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    def __repr__(self) -> str:
        return f"<SessionLog(id={self.id}, source={self.source.value}, session_id={self.session_id})>"


class AnalysisJob(Base):
    """Hook effectiveness analysis job."""

    __tablename__ = "analysis_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_filter: Mapped[Optional[LogSource]] = mapped_column(Enum(LogSource), nullable=True)
    session_type_filter: Mapped[Optional[SessionType]] = mapped_column(Enum(SessionType), nullable=True)
    date_from: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    date_to: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[AnalysisStatus] = mapped_column(Enum(AnalysisStatus), default=AnalysisStatus.PENDING, nullable=False, index=True)
    progress: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_logs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processed_logs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False, index=True
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<AnalysisJob(id={self.id}, name='{self.name}', status={self.status.value})>"


class AnalysisResult(Base):
    """Aggregated analysis results."""

    __tablename__ = "analysis_results"
    __table_args__ = (
        UniqueConstraint("job_id", "source", "session_type", name="uq_analysis_result"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("analysis_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    source: Mapped[LogSource] = mapped_column(Enum(LogSource), nullable=False)
    session_type: Mapped[SessionType] = mapped_column(Enum(SessionType), nullable=False)
    total_sessions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hook_reach_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hook_reach_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    router_open_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    router_open_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    playbook_open_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    playbook_open_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    principle_open_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    principle_open_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    opens_per_100_prompts: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    def __repr__(self) -> str:
        return f"<AnalysisResult(job_id={self.job_id}, source={self.source.value}, session_type={self.session_type.value}, opens_per_100={self.opens_per_100_prompts})>"