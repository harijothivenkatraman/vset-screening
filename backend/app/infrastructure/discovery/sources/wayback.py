"""Wayback Machine archive evidence source."""
from __future__ import annotations

from datetime import datetime, timezone
import logging
import re
from typing import Any
import httpx

from app.application.ports.evidence_source_port import (
    DiscoveryContext,
    EvidenceItem,
    EvidenceSourcePort,
    ExtractedField,
    ReliabilityTier,
)

logger = logging.getLogger(__name__)

USER_AGENT = "vSET-CompanyDiscovery/1.0 (+https://vset.io/bot; research@vset.io)"


class WaybackSource(EvidenceSourcePort):
    """Historical archive snapshot and first-seen date source."""

    def __init__(self, timeout_seconds: float = 8.0) -> None:
        self._timeout_seconds = timeout_seconds

    @property
    def name(self) -> str:
        return "wayback"

    @property
    def reliability_tier(self) -> ReliabilityTier:
        return ReliabilityTier.LOW

    @property
    def fields_supported(self) -> list[str]:
        return ["snapshot_date", "snapshot_url"]

    async def applies_to(self, context: DiscoveryContext) -> bool:
        return bool(context.website_url or context.confirmed_urls.get("website"))

    async def collect(
        self, context: DiscoveryContext
    ) -> tuple[list[EvidenceItem], dict[str, Any]]:
        target_url = context.website_url or context.confirmed_urls.get("website")
        if not target_url:
            return [], {
                "outcome": "empty_text",
                "bytes_fetched": 0,
                "fields_extracted": [],
                "error_details": "No website URL in context",
            }

        now_iso = datetime.now(timezone.utc).isoformat()
        api_url = f"https://archive.org/wayback/available?url={target_url}"

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds,
                headers={"User-Agent": USER_AGENT},
                follow_redirects=True,
            ) as client:
                resp = await client.get(api_url)
                if resp.status_code != 200:
                    return [], {
                        "outcome": f"http_error:{resp.status_code}",
                        "bytes_fetched": len(resp.content),
                        "fields_extracted": [],
                        "error_details": f"Wayback API returned {resp.status_code}",
                    }

                data = resp.json()

        except httpx.TimeoutException:
            return [], {
                "outcome": "timeout",
                "bytes_fetched": 0,
                "fields_extracted": [],
                "error_details": f"Wayback API timed out after {self._timeout_seconds}s",
            }
        except Exception as exc:
            return [], {
                "outcome": "http_error:client_error",
                "bytes_fetched": 0,
                "fields_extracted": [],
                "error_details": str(exc),
            }

        snapshots = data.get("archived_snapshots", {})
        closest = snapshots.get("closest")
        if not closest or not closest.get("available"):
            return [], {
                "outcome": "empty_text",
                "bytes_fetched": len(resp.content),
                "fields_extracted": [],
                "error_details": f"No archive snapshots found for {target_url}",
            }

        snap_url = closest.get("url", "")
        timestamp = closest.get("timestamp", "")
        extracted_fields: list[ExtractedField] = []

        if timestamp:
            match = re.match(r"^(\d{4})", timestamp)
            if match:
                year = match.group(1)
                extracted_fields.append(
                    ExtractedField(
                        field_name="snapshot_date",
                        value=f"Web archive snapshot observed: {year}",
                        exact_quote=f"Earliest web archive snapshot observed in {year} ({timestamp})",
                        confidence=0.4,
                    )
                )

        if snap_url:
            extracted_fields.append(
                ExtractedField(
                    field_name="snapshot_url",
                    value=snap_url,
                    exact_quote=f"Wayback Machine snapshot URL: {snap_url}",
                    confidence=1.0,
                )
            )

        item = EvidenceItem(
            source_id=f"src_wayback_{timestamp[:8] if timestamp else 'snap'}",
            source_type="WEB",
            url=snap_url or api_url,
            retrieved_at=now_iso,
            extracted_fields=extracted_fields,
            excerpt=f"Internet Archive Wayback snapshot for {target_url} from {timestamp}.",
            publisher="Internet Archive Wayback Machine",
            title=f"Wayback snapshot for {target_url}",
        )

        return [item], {
            "outcome": "ok",
            "bytes_fetched": len(resp.content),
            "fields_extracted": [f.field_name for f in extracted_fields],
            "error_details": None,
        }
