from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from app.domain.entities.section import Section


def map_sections_from_raw(raw_data: dict[str, Any], report_id: UUID) -> list[Section]:
    sections_raw = raw_data.get("canonical", {}).get("content", {}).get("sections", [])
    now = datetime.now(timezone.utc)
    sections: list[Section] = []

    for idx, sec in enumerate(sections_raw):
        sections.append(
            Section(
                id=uuid4(),
                report_id=report_id,
                key=sec.get("key", f"section-{idx}"),
                title=sec.get("title", ""),
                position=idx,
                ribbon=sec.get("ribbon", []),
                blocks=sec.get("blocks", []),
                created_at=now,
            )
        )

    return sections
