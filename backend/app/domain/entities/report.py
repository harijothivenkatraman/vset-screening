from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class Report:
    id: UUID
    company_id: UUID
    canonical_screen_id: str
    report_id: str | None
    final_fingerprint: str
    audience: str
    audience_label: str
    version: str
    canonical_version: str
    schema_version: str
    research_cutoff: str | None
    as_of_date: str | None
    generated_at: datetime | None
    cover: dict[str, Any]
    ribbon: list[list[str]]
    presentation: dict[str, Any]
    report_basis: dict[str, Any]
    concerns_conflicts: dict[str, Any]
    created_at: datetime
    updated_at: datetime
