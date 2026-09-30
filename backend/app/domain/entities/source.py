from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class Source:
    id: UUID
    report_id: UUID
    source_id: str
    title: str | None
    publisher: str | None
    published_date: str | None
    display_url: str | None
    canonical_url: str | None
    source_type: str | None
    ownership_class: str | None
    position: int
    created_at: datetime
