"""Port for extracting structured report data from evidence."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
from app.domain.entities.discovery import Evidence


class ReportExtractorPort(ABC):
    """Extract structured report data from collected evidence."""
    
    @abstractmethod
    async def extract(
        self,
        evidence: Evidence,
        company_name: str,
        founder_names: list[str],
    ) -> dict[str, Any]:
        """Extract report data from evidence.
        
        Returns a dict conforming to the canonical report JSON schema:
        {canonical: {meta, content: {cover, sections, ...}}, meta, presentation}
        
        Partial data is expected — missing fields should be marked
        'Not established' with appropriate 'Information to prepare' items.
        """
        ...
