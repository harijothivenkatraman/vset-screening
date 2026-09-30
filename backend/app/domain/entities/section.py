from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class Section:
    id: UUID
    report_id: UUID
    key: str
    title: str
    position: int
    ribbon: list[list[str]]
    blocks: list[Any]
    created_at: datetime
