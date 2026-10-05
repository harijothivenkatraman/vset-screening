"""FastAPI router for the Company Discovery endpoints."""
from __future__ import annotations

import logging
import shutil
import sys
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from app.application.ports.job_store_port import JobStorePort
from app.application.ports.llm_port import LlmPort
from app.application.services.build_report import BuildReportService
from app.application.services.get_discovery_job import GetDiscoveryJobService
from app.application.services.resolve_candidates import (
    ResolveCandidatesService,
    ResolveInput,
)
from app.application.services.start_discovery_job import (
    StartDiscoveryJobService,
    StartJobInput,
)
from app.config import get_settings
from app.domain.exceptions import (
    DiscoveryDisabledError,
    JobNotFoundError,
    SearchUnavailableError,
)
from app.presentation.dependencies import (
    get_build_report_service,
    get_discovery_job_service,
    get_job_store_port,
    get_llm_port,
    get_resolve_candidates_service,
    get_start_discovery_job_service,
)
from app.presentation.guards.api_key_guard import verify_admin_key
from app.presentation.schemas.discovery import (
    CandidateItemSchema,
    DiscoveryHealthResponse,
    DiscoveryJobStatusResponse,
    ResolveCandidatesRequest,
    ResolveCandidatesResponse,
    StartDiscoveryJobRequest,
    StartDiscoveryJobResponse,
    SourceDiagnosticSchema,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/discovery", tags=["discovery"])
settings = get_settings()


def _get_free_disk_gb() -> float:
    """Get available free disk space in GB."""
    try:
        path = "C:\\" if sys.platform == "win32" else "/"
        total, used, free = shutil.disk_usage(path)
        return free / (1024 ** 3)
    except Exception:
        return 10.0


async def _run_job_in_background(
    build_service: BuildReportService,
    job_store: JobStorePort,
    job_id: str,
) -> None:
    """Background task executor for BuildReportService."""
    job = await job_store.get(job_id)
    if not job:
        logger.error("Background task: job '%s' not found in store", job_id)
        return
    await build_service.execute(job)


@router.post(
    "/resolve",
    response_model=ResolveCandidatesResponse,
    dependencies=[Depends(verify_admin_key)],
    summary="Search and resolve candidate profile/website URLs",
)
async def resolve_candidates(
    request: ResolveCandidatesRequest,
    service: ResolveCandidatesService = Depends(get_resolve_candidates_service),
) -> ResolveCandidatesResponse:
    """Search for relevant candidate URLs for a company and its founders."""
    input_dto = ResolveInput(
        company_name=request.company_name,
        founder_names=request.founder_names,
        website_override=request.website_override,
        company_linkedin_override=request.company_linkedin_override,
        founder_linkedin_overrides=request.founder_linkedin_overrides,
    )

    try:
        output = await service.execute(input_dto)
    except SearchUnavailableError as exc:
        return ResolveCandidatesResponse(
            candidates={},
            search_unavailable=True,
            error_message=exc.message,
        )

    candidates_schema: dict[str, list[CandidateItemSchema]] = {}
    for cat, items in output.candidates.items():
        candidates_schema[cat] = [
            CandidateItemSchema(
                url=c.url,
                title=c.title,
                snippet=c.snippet,
                domain=c.domain,
                confidence=c.confidence,
                category=c.category,
                search_query=c.search_query,
                entity_name=c.entity_name,
            )
            for c in items
        ]

    return ResolveCandidatesResponse(
        candidates=candidates_schema,
        search_unavailable=output.search_unavailable,
        error_message=output.error_message,
    )


@router.post(
    "/jobs",
    response_model=StartDiscoveryJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(verify_admin_key)],
    summary="Start background screening discovery job",
)
async def start_discovery_job(
    request: StartDiscoveryJobRequest,
    background_tasks: BackgroundTasks,
    service: StartDiscoveryJobService = Depends(get_start_discovery_job_service),
    build_service: BuildReportService = Depends(get_build_report_service),
    job_store: JobStorePort = Depends(get_job_store_port),
    llm: LlmPort = Depends(get_llm_port),
) -> StartDiscoveryJobResponse:
    """Enqueues a background discovery job. Returns 202 Accepted with job ID."""
    # 1. Disk space guard
    free_gb = _get_free_disk_gb()
    if free_gb < settings.DISCOVERY_MIN_FREE_DISK_GB:
        raise HTTPException(
            status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
            detail=f"Insufficient free disk space ({free_gb:.1f} GB available, {settings.DISCOVERY_MIN_FREE_DISK_GB:.1f} GB required).",
        )

    # 2. Rate limiting (max N jobs per hour)
    recent_jobs = await job_store.list_recent(limit=50)
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    recent_hour_count = sum(1 for j in recent_jobs if j.created_at >= one_hour_ago)
    if recent_hour_count >= settings.DISCOVERY_RATE_LIMIT_PER_HOUR:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: maximum {settings.DISCOVERY_RATE_LIMIT_PER_HOUR} discovery jobs per hour.",
        )

    # 2b. Concurrency guard: one job at a time across the system
    active_jobs = [j for j in recent_jobs if str(getattr(j, "state", "")).lower() in ("queued", "running")]
    if active_jobs:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A discovery job ({active_jobs[0].id}) is currently in progress for '{active_jobs[0].company_name}'. Only one discovery job at a time is permitted.",
        )

    # 2c. Cooldown guard: prevent rapid repeat refresh on the same company (60s cooldown)
    company_norm = request.company_name.strip().lower()
    now_utc = datetime.now(timezone.utc)
    for j in recent_jobs:
        if j.company_name.strip().lower() == company_norm and (now_utc - j.created_at) < timedelta(seconds=60):
            remaining = int(60 - (now_utc - j.created_at).total_seconds())
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Refresh cooldown active for '{request.company_name}'. Please wait {max(1, remaining)} seconds before refreshing again.",
            )


    # 2b. Verify LLM model availability on inference server
    llm_warning: str | None = None
    if settings.DISCOVERY_ENABLED:
        try:
            if hasattr(llm, "check_availability"):
                avail = await llm.check_availability()
                if not avail.get("model_available", False):
                    llm_warning = "LLM model not available; assembled with rules-only extraction"
        except Exception as exc:
            logger.warning("LLM availability check failed during job submission: %s", exc)

    # 3. Create job entity
    try:
        res = await service.execute(
            StartJobInput(
                company_name=request.company_name,
                founder_names=request.founder_names,
                confirmed_urls=request.confirmed_urls,
                search_snippets=request.search_snippets,
                manual_evidence={k: v.model_dump() for k, v in request.manual_evidence.items()},
                llm_model=request.llm_model,
            )
        )
        if llm_warning:
            job = await job_store.get(res.job_id)
            if job:
                job.add_warning(llm_warning)
                await job_store.update(job)
    except DiscoveryDisabledError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=exc.message) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    # 4. Enqueue background execution
    background_tasks.add_task(_run_job_in_background, build_service, job_store, res.job_id)

    return StartDiscoveryJobResponse(
        job_id=res.job_id,
        state=res.state,
        message=res.message,
    )


@router.get(
    "/jobs/{job_id}",
    response_model=DiscoveryJobStatusResponse,
    dependencies=[Depends(verify_admin_key)],
    summary="Poll discovery job status",
)
async def get_job_status(
    job_id: str,
    service: GetDiscoveryJobService = Depends(get_discovery_job_service),
) -> DiscoveryJobStatusResponse:
    """Retrieve the progress and status of a discovery job."""
    try:
        status_dto = await service.execute(job_id)
        return DiscoveryJobStatusResponse(
            job_id=status_dto.job_id,
            company_name=status_dto.company_name,
            state=status_dto.state,
            stage=status_dto.stage,
            progress=status_dto.progress,
            warnings=status_dto.warnings,
            result_slug=status_dto.result_slug,
            error_message=status_dto.error_message,
            diagnostics=[
                SourceDiagnosticSchema(
                    url=d.url,
                    outcome=d.outcome,
                    bytes_fetched=d.bytes_fetched,
                    fields_extracted=d.fields_extracted,
                    error_details=d.error_details,
                )
                for d in status_dto.diagnostics
            ],
        )
    except JobNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Discovery job '{job_id}' not found.",
        )


@router.get(
    "/health",
    response_model=DiscoveryHealthResponse,
    summary="Discovery subsystem health and LLM reachability probe",
)
async def discovery_health(
    llm: LlmPort = Depends(get_llm_port),
) -> DiscoveryHealthResponse:
    """Public probe to check readiness of discovery components and LLM server."""
    is_llm_ok = False
    is_model_ok = False
    installed_models: list[str] = []
    try:
        if hasattr(llm, "check_availability"):
            avail = await llm.check_availability()
            is_llm_ok = avail.get("reachable", False)
            is_model_ok = avail.get("model_available", False)
        else:
            is_llm_ok = await llm.is_available()
            is_model_ok = is_llm_ok
            
        import httpx
        base = settings.LLM_BASE_URL.replace("/v1", "").rstrip("/")
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{base}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                installed_models = [str(m["name"]) for m in data.get("models", []) if isinstance(m, dict) and "name" in m]
    except Exception:
        pass

    free_gb = _get_free_disk_gb()

    status_str = "healthy" if (is_model_ok or not settings.DISCOVERY_ENABLED) else "degraded"

    return DiscoveryHealthResponse(
        status=status_str,
        discovery_enabled=settings.DISCOVERY_ENABLED,
        llm_reachable=is_llm_ok,
        model_available=is_model_ok,
        llm_model=settings.LLM_MODEL,
        installed_models=installed_models,
        search_providers=settings.SEARCH_PROVIDERS,
        free_disk_gb=round(free_gb, 2),
    )
