# backend/app/api/analysis.py
"""Hook effectiveness analysis API endpoints."""
from datetime import UTC, datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.analysis import (
    SessionLog,
    LogSource,
    SessionType,
    AnalysisJob,
    AnalysisStatus,
    AnalysisResult,
)


router = APIRouter(prefix="/analyze", tags=["analysis"])


# Request/Response Models
class SessionLogCreate(BaseModel):
    """Session log creation request."""
    source: LogSource
    session_id: str = Field(..., min_length=1, max_length=255)
    session_type: SessionType
    timestamp: datetime
    hook_present: bool = False
    hook_text: Optional[str] = None
    router_opened: bool = False
    playbook_opened: bool = False
    principle_opened: bool = False
    agent_type_detail: Optional[str] = Field(default=None, max_length=100)
    raw_log_path: Optional[str] = Field(default=None, max_length=500)
    metadata_json: Optional[str] = None


class SessionLogResponse(BaseModel):
    """Session log response."""
    id: int
    source: LogSource
    session_id: str
    session_type: SessionType
    timestamp: datetime
    hook_present: bool
    hook_text: Optional[str]
    router_opened: bool
    playbook_opened: bool
    principle_opened: bool
    agent_type_detail: Optional[str]
    raw_log_path: Optional[str]
    metadata_json: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class SessionLogListResponse(BaseModel):
    """Paginated session log list response."""
    items: list[SessionLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AnalysisJobCreate(BaseModel):
    """Analysis job creation request."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    source_filter: Optional[LogSource] = None
    session_type_filter: Optional[SessionType] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class AnalysisJobResponse(BaseModel):
    """Analysis job response."""
    id: int
    name: str
    description: Optional[str]
    source_filter: Optional[LogSource]
    session_type_filter: Optional[SessionType]
    date_from: Optional[datetime]
    date_to: Optional[datetime]
    status: AnalysisStatus
    progress: float
    total_logs: int
    processed_logs: int
    error_message: Optional[str]
    result_json: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class AnalysisJobListResponse(BaseModel):
    """Paginated analysis job list response."""
    items: list[AnalysisJobResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AnalysisResultResponse(BaseModel):
    """Analysis result response."""
    id: int
    job_id: int
    source: LogSource
    session_type: SessionType
    total_sessions: int
    hook_reach_count: int
    hook_reach_rate: float
    router_open_count: int
    router_open_rate: float
    playbook_open_count: int
    playbook_open_rate: float
    principle_open_count: int
    principle_open_rate: float
    opens_per_100_prompts: float
    created_at: datetime

    class Config:
        from_attributes = True


class EffectivenessReportResponse(BaseModel):
    """Complete effectiveness report response."""
    job: AnalysisJobResponse
    results: list[AnalysisResultResponse]
    summary: dict


# Helper functions
def job_to_response(job: AnalysisJob) -> AnalysisJobResponse:
    """Convert AnalysisJob ORM to response model."""
    return AnalysisJobResponse(
        id=job.id,
        name=job.name,
        description=job.description,
        source_filter=job.source_filter,
        session_type_filter=job.session_type_filter,
        date_from=job.date_from,
        date_to=job.date_to,
        status=job.status,
        progress=job.progress,
        total_logs=job.total_logs,
        processed_logs=job.processed_logs,
        error_message=job.error_message,
        result_json=job.result_json,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


def result_to_response(result: AnalysisResult) -> AnalysisResultResponse:
    """Convert AnalysisResult ORM to response model."""
    return AnalysisResultResponse(
        id=result.id,
        job_id=result.job_id,
        source=result.source,
        session_type=result.session_type,
        total_sessions=result.total_sessions,
        hook_reach_count=result.hook_reach_count,
        hook_reach_rate=result.hook_reach_rate,
        router_open_count=result.router_open_count,
        router_open_rate=result.router_open_rate,
        playbook_open_count=result.playbook_open_count,
        playbook_open_rate=result.playbook_open_rate,
        principle_open_count=result.principle_open_count,
        principle_open_rate=result.principle_open_rate,
        opens_per_100_prompts=result.opens_per_100_prompts,
        created_at=result.created_at,
    )


def log_to_response(log: SessionLog) -> SessionLogResponse:
    """Convert SessionLog ORM to response model."""
    return SessionLogResponse(
        id=log.id,
        source=log.source,
        session_id=log.session_id,
        session_type=log.session_type,
        timestamp=log.timestamp,
        hook_present=log.hook_present,
        hook_text=log.hook_text,
        router_opened=log.router_opened,
        playbook_opened=log.playbook_opened,
        principle_opened=log.principle_opened,
        agent_type_detail=log.agent_type_detail,
        raw_log_path=log.raw_log_path,
        metadata_json=log.metadata_json,
        created_at=log.created_at,
    )


# Session Log Endpoints
@router.post("/logs", response_model=SessionLogResponse, status_code=status.HTTP_201_CREATED)
async def create_session_log(
    log_data: SessionLogCreate,
    session: AsyncSession = Depends(get_session),
) -> SessionLogResponse:
    """Create a new session log entry."""
    log = SessionLog(**log_data.model_dump())
    session.add(log)
    await session.commit()
    await session.refresh(log)
    return log_to_response(log)


@router.post("/logs/bulk", response_model=list[SessionLogResponse], status_code=status.HTTP_201_CREATED)
async def create_session_logs_bulk(
    logs_data: list[SessionLogCreate],
    session: AsyncSession = Depends(get_session),
) -> list[SessionLogResponse]:
    """Create multiple session log entries in bulk."""
    logs = [SessionLog(**data.model_dump()) for data in logs_data]
    session.add_all(logs)
    await session.commit()
    for log in logs:
        await session.refresh(log)
    return [log_to_response(log) for log in logs]


@router.get("/logs", response_model=SessionLogListResponse)
async def list_session_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    source: Optional[LogSource] = None,
    session_type: Optional[SessionType] = None,
    hook_present: Optional[bool] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    session: AsyncSession = Depends(get_session),
) -> SessionLogListResponse:
    """List session logs with pagination and filtering."""
    query = select(SessionLog)
    count_query = select(func.count(SessionLog.id))

    if source:
        query = query.where(SessionLog.source == source)
        count_query = count_query.where(SessionLog.source == source)
    if session_type:
        query = query.where(SessionLog.session_type == session_type)
        count_query = count_query.where(SessionLog.session_type == session_type)
    if hook_present is not None:
        query = query.where(SessionLog.hook_present == hook_present)
        count_query = count_query.where(SessionLog.hook_present == hook_present)
    if date_from:
        query = query.where(SessionLog.timestamp >= date_from)
        count_query = count_query.where(SessionLog.timestamp >= date_from)
    if date_to:
        query = query.where(SessionLog.timestamp <= date_to)
        count_query = count_query.where(SessionLog.timestamp <= date_to)

    total_result = await session.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(SessionLog.timestamp.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    logs = result.scalars().all()

    return SessionLogListResponse(
        items=[log_to_response(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


# Analysis Job Endpoints
@router.post("/jobs", response_model=AnalysisJobResponse, status_code=status.HTTP_201_CREATED)
async def create_analysis_job(
    job_data: AnalysisJobCreate,
    session: AsyncSession = Depends(get_session),
) -> AnalysisJobResponse:
    """Create a new analysis job."""
    # Count matching logs
    query = select(func.count(SessionLog.id))
    if job_data.source_filter:
        query = query.where(SessionLog.source == job_data.source_filter)
    if job_data.session_type_filter:
        query = query.where(SessionLog.session_type == job_data.session_type_filter)
    if job_data.date_from:
        query = query.where(SessionLog.timestamp >= job_data.date_from)
    if job_data.date_to:
        query = query.where(SessionLog.timestamp <= job_data.date_to)

    total_logs_result = await session.execute(query)
    total_logs = total_logs_result.scalar_one()

    job = AnalysisJob(
        **job_data.model_dump(),
        total_logs=total_logs,
        status=AnalysisStatus.PENDING,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job_to_response(job)


@router.get("/jobs", response_model=AnalysisJobListResponse)
async def list_analysis_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[AnalysisStatus] = None,
    session: AsyncSession = Depends(get_session),
) -> AnalysisJobListResponse:
    """List analysis jobs with pagination."""
    query = select(AnalysisJob)
    count_query = select(func.count(AnalysisJob.id))

    if status:
        query = query.where(AnalysisJob.status == status)
        count_query = count_query.where(AnalysisJob.status == status)

    total_result = await session.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(AnalysisJob.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    jobs = result.scalars().all()

    return AnalysisJobListResponse(
        items=[job_to_response(job) for job in jobs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/jobs/{job_id}", response_model=AnalysisJobResponse)
async def get_analysis_job(
    job_id: int,
    session: AsyncSession = Depends(get_session),
) -> AnalysisJobResponse:
    """Get analysis job by ID."""
    job = await session.get(AnalysisJob, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis job not found")
    return job_to_response(job)


@router.post("/jobs/{job_id}/run", response_model=AnalysisJobResponse)
async def run_analysis_job(
    job_id: int,
    session: AsyncSession = Depends(get_session),
) -> AnalysisJobResponse:
    """Run an analysis job (compute effectiveness metrics)."""
    job = await session.get(AnalysisJob, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis job not found")

    if job.status == AnalysisStatus.RUNNING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Job already running")

    job.status = AnalysisStatus.RUNNING
    job.started_at = datetime.now(UTC)
    job.progress = 0.0
    await session.commit()

    try:
        # Query logs for this job
        query = select(SessionLog)
        if job.source_filter:
            query = query.where(SessionLog.source == job.source_filter)
        if job.session_type_filter:
            query = query.where(SessionLog.session_type == job.session_type_filter)
        if job.date_from:
            query = query.where(SessionLog.timestamp >= job.date_from)
        if job.date_to:
            query = query.where(SessionLog.timestamp <= job.date_to)

        logs_result = await session.execute(query)
        logs = logs_result.scalars().all()

        job.total_logs = len(logs)
        job.processed_logs = 0

        # Group by source and session_type
        from collections import defaultdict
        grouped: dict[tuple[LogSource, SessionType], list[SessionLog]] = defaultdict(list)
        for log in logs:
            grouped[(log.source, log.session_type)].append(log)

        results = []
        for (source, session_type), group_logs in grouped.items():
            total = len(group_logs)
            hook_reach = sum(1 for l in group_logs if l.hook_present)
            router_opens = sum(1 for l in group_logs if l.router_opened)
            playbook_opens = sum(1 for l in group_logs if l.playbook_opened)
            principle_opens = sum(1 for l in group_logs if l.principle_opened)

            # Calculate rates
            hook_reach_rate = (hook_reach / total * 100) if total > 0 else 0.0
            router_open_rate = (router_opens / total * 100) if total > 0 else 0.0
            playbook_open_rate = (playbook_opens / total * 100) if total > 0 else 0.0
            principle_open_rate = (principle_opens / total * 100) if total > 0 else 0.0

            # Opens per 100 prompts (using hook reach as denominator for fairness)
            opens_per_100 = (router_opens / hook_reach * 100) if hook_reach > 0 else 0.0

            result = AnalysisResult(
                job_id=job.id,
                source=source,
                session_type=session_type,
                total_sessions=total,
                hook_reach_count=hook_reach,
                hook_reach_rate=hook_reach_rate,
                router_open_count=router_opens,
                router_open_rate=router_open_rate,
                playbook_open_count=playbook_opens,
                playbook_open_rate=playbook_open_rate,
                principle_open_count=principle_opens,
                principle_open_rate=principle_open_rate,
                opens_per_100_prompts=opens_per_100,
            )
            results.append(result)

        # Save results
        for result in results:
            session.add(result)

        job.status = AnalysisStatus.COMPLETED
        job.completed_at = datetime.now(UTC)
        job.progress = 100.0
        job.processed_logs = job.total_logs

        # Generate summary JSON
        import json
        # Build summary by source and session type
        by_source: dict = {}
        for r in results:
            src_key = r.source.value
            st_key = r.session_type.value
            if src_key not in by_source:
                by_source[src_key] = {}
            by_source[src_key][st_key] = {
                "total_sessions": r.total_sessions,
                "hook_reach_rate": r.hook_reach_rate,
                "router_open_rate": r.router_open_rate,
                "playbook_open_rate": r.playbook_open_rate,
                "principle_open_rate": r.principle_open_rate,
                "opens_per_100_prompts": r.opens_per_100_prompts,
            }

        summary = {
            "total_sessions_analyzed": sum(r.total_sessions for r in results),
            "by_source": by_source,
        }
        job.result_json = json.dumps(summary, default=str)

        await session.commit()
        await session.refresh(job)

    except Exception as e:
        job.status = AnalysisStatus.FAILED
        job.error_message = str(e)
        job.completed_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(job)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Analysis failed: {e}")

    return job_to_response(job)


@router.get("/jobs/{job_id}/report", response_model=EffectivenessReportResponse)
async def get_effectiveness_report(
    job_id: int,
    session: AsyncSession = Depends(get_session),
) -> EffectivenessReportResponse:
    """Get complete effectiveness report for a completed job."""
    job = await session.get(AnalysisJob, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis job not found")

    if job.status != AnalysisStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job not completed (status: {job.status.value})",
        )

    results_query = select(AnalysisResult).where(AnalysisResult.job_id == job_id)
    results_result = await session.execute(results_query)
    results = results_result.scalars().all()

    # Build summary with nested by_source structure
    by_source: dict = {}
    for r in results:
        src_key = r.source.value
        st_key = r.session_type.value
        if src_key not in by_source:
            by_source[src_key] = {}
        by_source[src_key][st_key] = {
            "total_sessions": r.total_sessions,
            "hook_reach_rate": r.hook_reach_rate,
            "router_open_rate": r.router_open_rate,
            "playbook_open_rate": r.playbook_open_rate,
            "principle_open_rate": r.principle_open_rate,
            "opens_per_100_prompts": r.opens_per_100_prompts,
        }

    summary = {
        "total_sessions_analyzed": sum(r.total_sessions for r in results),
        "by_source": by_source,
    }

    return EffectivenessReportResponse(
        job=job_to_response(job),
        results=[result_to_response(r) for r in results],
        summary=summary,
    )


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_analysis_job(
    job_id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete an analysis job and its results."""
    job = await session.get(AnalysisJob, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis job not found")

    await session.delete(job)
    await session.commit()