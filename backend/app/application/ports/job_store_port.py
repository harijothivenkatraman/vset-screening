"""Port for discovery job storage."""
from __future__ import annotations
from abc import ABC, abstractmethod
from app.domain.entities.discovery import DiscoveryJob


class JobStorePort(ABC):
    """Store and retrieve discovery jobs. In-memory, capped."""
    
    @abstractmethod
    async def create(self, job: DiscoveryJob) -> DiscoveryJob:
        """Store a new job."""
        ...
    
    @abstractmethod
    async def get(self, job_id: str) -> DiscoveryJob | None:
        """Get job by ID. Returns None if not found or evicted."""
        ...
    
    @abstractmethod
    async def update(self, job: DiscoveryJob) -> None:
        """Update an existing job."""
        ...
    
    @abstractmethod
    async def list_recent(self, limit: int = 10) -> list[DiscoveryJob]:
        """List recent jobs, newest first."""
        ...
