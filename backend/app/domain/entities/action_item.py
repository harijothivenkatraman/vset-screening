from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class ActionItem:
    id: UUID
    report_id: UUID
    action_id: str
    kind: str
    where: str | None
    domain: str | None
    topic: str | None
    group_name: str | None
    text: str
    why: str | None
    key: str | None
    semantic_key: str | None
    priority_level: str | None
    position: int
    created_at: datetime
