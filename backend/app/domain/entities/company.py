from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class Company:
    id: UUID
    slug: str
    name: str
    website: str | None
    created_at: datetime
    updated_at: datetime
