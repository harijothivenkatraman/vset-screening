"""In-memory bounded job store implementation of JobStorePort."""
from __future__ import annotations

import asyncio
from app.application.ports.job_store_port import JobStorePort
from app.domain.entities.discovery import DiscoveryJob


class InMemoryJobStore(JobStorePort):
    """Stores discovery jobs in memory with bounded capacity."""

    def __init__(self, max_jobs: int = 20) -> None:
        self._max_jobs = max_jobs
        self._jobs: dict[str, DiscoveryJob] = {}
        self._lock = asyncio.Lock()

    async def create(self, job: DiscoveryJob) -> DiscoveryJob:
        async with self._lock:
            if len(self._jobs) >= self._max_jobs:
                # Evict oldest job based on created_at
                oldest_id = min(self._jobs.keys(), key=lambda j_id: self._jobs[j_id].created_at)
                self._jobs.pop(oldest_id, None)
            self._jobs[job.id] = job
            return job

    async def get(self, job_id: str) -> DiscoveryJob | None:
        async with self._lock:
            return self._jobs.get(job_id)

    async def update(self, job: DiscoveryJob) -> None:
        async with self._lock:
            self._jobs[job.id] = job

    async def list_recent(self, limit: int = 10) -> list[DiscoveryJob]:
        async with self._lock:
            sorted_jobs = sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)
            return sorted_jobs[:limit]
