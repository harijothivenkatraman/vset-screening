"""Use case: start a discovery job."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.application.ports.job_store_port import JobStorePort
from app.domain.entities.discovery import DiscoveryJob, JobState
from app.domain.exceptions import DiscoveryDisabledError


@dataclass(frozen=True)
class StartJobInput:
    company_name: str
    founder_names: list[str]
    confirmed_urls: dict[str, str]  # category -> confirmed URL
    search_snippets: dict[str, str] = field(default_factory=dict)
    manual_evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StartJobOutput:
    job_id: str
    state: str
    message: str


class StartDiscoveryJobService:
    """Create a discovery job and return its ID.
    
    The actual background execution is handled by the presentation layer
    (FastAPI BackgroundTasks). This service only creates the job entity.
    """
    
    def __init__(
        self,
        job_store: JobStorePort,
        *,
        discovery_enabled: bool = True,
    ) -> None:
        self._job_store = job_store
        self._discovery_enabled = discovery_enabled
    
    async def execute(self, input_dto: StartJobInput) -> StartJobOutput:
        if not self._discovery_enabled:
            raise DiscoveryDisabledError()
        
        if not input_dto.company_name.strip():
            raise ValueError("Company name is required")
        if not input_dto.founder_names or not any(n.strip() for n in input_dto.founder_names):
            raise ValueError("At least one founder name is required")
        
        now = datetime.now(timezone.utc)
        job = DiscoveryJob(
            id=str(uuid.uuid4()),
            company_name=input_dto.company_name.strip(),
            founder_names=[n.strip() for n in input_dto.founder_names if n.strip()],
            state=JobState.QUEUED,
            stage="Queued",
            progress=0.0,
            warnings=[],
            result_slug=None,
            created_at=now,
            updated_at=now,
            confirmed_urls=input_dto.confirmed_urls,
            search_snippets=input_dto.search_snippets,
            manual_evidence=input_dto.manual_evidence,
        )
        
        await self._job_store.create(job)
        
        return StartJobOutput(
            job_id=job.id,
            state=job.state.value,
            message=f"Discovery job created for '{job.company_name}'",
        )
