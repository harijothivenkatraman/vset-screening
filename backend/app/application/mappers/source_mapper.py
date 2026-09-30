from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from app.domain.entities.source import Source


def map_sources_from_raw(raw_data: dict[str, Any], report_id: UUID) -> list[Source]:
    sources_raw = (
        raw_data.get("canonical", {})
        .get("content", {})
        .get("final", {})
        .get("evidence_register", {})
        .get("sources", [])
    )
    now = datetime.now(timezone.utc)
    sources: list[Source] = []

    for idx, s in enumerate(sources_raw):
        sources.append(
            Source(
                id=uuid4(),
                report_id=report_id,
                source_id=s.get("source_id", f"src_{idx}"),
                title=s.get("title") or s.get("publisher") or s.get("display_url") or "",
                publisher=s.get("publisher"),
                published_date=s.get("published_date"),
                display_url=s.get("display_url"),
                canonical_url=s.get("canonical_url"),
                source_type=s.get("source_type"),
                ownership_class=s.get("ownership_class"),
                position=idx,
                created_at=now,
            )
        )

    return sources
