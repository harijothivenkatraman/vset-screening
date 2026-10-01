"""Port for importing reports into the database."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ImportResult:
    """Result of a report import operation."""
    status: str          # "created" | "updated" | "unchanged"
    company_slug: str
    message: str


class ReportImportPort(ABC):
    """Import a structured report into the database."""
    
    @abstractmethod
    async def import_report(self, raw_data: dict[str, Any]) -> ImportResult:
        """Import a report. Handles version gate, validation, and idempotency.
        
        Args:
            raw_data: Full canonical JSON report tree.
        
        Returns:
            ImportResult with status, slug, and message.
        
        Raises:
            ValueError: If the report fails schema validation.
        """
        ...
