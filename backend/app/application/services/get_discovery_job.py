"""Use case: get discovery job status."""
from __future__ import annotations

from dataclasses import dataclass

from app.application.ports.job_store_port import JobStorePort
from app.domain.exceptions import JobNotFoundError


@dataclass(frozen=True)
class JobStatusOutput:
    job_id: str
    company_name: str
    state: str
    stage: str
    progress: float
    warnings: list[str]
    result_slug: str | None
    error_message: str | None


class GetDiscoveryJobService:
    """Retrieve the current status of a discovery job."""
    
    def __init__(self, job_store: JobStorePort) -> None:
        self._job_store = job_store
    
    async def execute(self, job_id: str) -> JobStatusOutput:
        job = await self._job_store.get(job_id)
        if job is None:
            raise JobNotFoundError(job_id)
        
        return JobStatusOutput(
            job_id=job.id,
            company_name=job.company_name,
            state=job.state.value,
            stage=job.stage,
            progress=job.progress,
            warnings=list(job.warnings),
            result_slug=job.result_slug,
            error_message=job.error_message,
        )
