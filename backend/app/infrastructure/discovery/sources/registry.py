"""Registry managing multi-source evidence collection plugins."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
import os
import time
from typing import Any

from app.application.ports.evidence_source_port import (
    DiscoveryContext,
    EvidenceItem,
    EvidenceRegistryPort,
    EvidenceSourcePort,
)
from app.domain.entities.discovery import SourceDiagnostic
from app.infrastructure.discovery.sources.news import NewsSource
from app.infrastructure.discovery.sources.rdap import RdapSource
from app.infrastructure.discovery.sources.wayback import WaybackSource
from app.infrastructure.discovery.sources.wikidata import WikidataSource

logger = logging.getLogger(__name__)

DEFAULT_ENABLED_SOURCES = "rdap,wikidata,news,wayback"


class SourceCircuitBreaker:
    """Per-source circuit breaker opening after 3 consecutive failures for 30 minutes."""

    def __init__(self, failure_threshold: int = 3, cooldown_seconds: float = 1800.0) -> None:
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.consecutive_failures = 0
        self.last_failure_time = 0.0

    def is_open(self) -> bool:
        if self.consecutive_failures >= self.failure_threshold:
            if time.time() - self.last_failure_time < self.cooldown_seconds:
                return True
            # Cooldown expired, half-open
            self.consecutive_failures = 0
        return False

    def record_success(self) -> None:
        self.consecutive_failures = 0

    def record_failure(self) -> None:
        self.consecutive_failures += 1
        self.last_failure_time = time.time()


class EvidenceSourceRegistry(EvidenceRegistryPort):
    """Registry for discovering, enabling, and orchestrating EvidenceSourcePort plugins (Open/Closed)."""

    def __init__(
        self,
        enabled_sources: list[str] | None = None,
        max_concurrency: int = 2,
    ) -> None:
        self._sources: dict[str, EvidenceSourcePort] = {}
        self._circuit_breakers: dict[str, SourceCircuitBreaker] = {}
        self._semaphore = asyncio.Semaphore(max_concurrency)

        if enabled_sources is None:
            env_val = os.getenv("DISCOVERY_SOURCES_ENABLED", DEFAULT_ENABLED_SOURCES)
            self._enabled_sources = {s.strip().lower() for s in env_val.split(",") if s.strip()}
        else:
            self._enabled_sources = {s.strip().lower() for s in enabled_sources if s.strip()}

        # Register default sources
        self.register(RdapSource())
        self.register(WikidataSource())
        self.register(NewsSource())
        self.register(WaybackSource())

    def register(self, source: EvidenceSourcePort) -> None:
        """Register a new source plugin without modifying orchestrator."""
        self._sources[source.name.lower()] = source
        if source.name.lower() not in self._circuit_breakers:
            self._circuit_breakers[source.name.lower()] = SourceCircuitBreaker()

    def get_source(self, name: str) -> EvidenceSourcePort | None:
        return self._sources.get(name.lower())

    async def collect_all(
        self, context: DiscoveryContext
    ) -> tuple[list[EvidenceItem], list[SourceDiagnostic]]:
        """Run all enabled and applicable sources respecting max concurrency and circuit breakers."""
        all_items: list[EvidenceItem] = []
        diagnostics: list[SourceDiagnostic] = []

        applicable_sources: list[EvidenceSourcePort] = []
        for name, source in self._sources.items():
            if name in self._enabled_sources:
                try:
                    if await source.applies_to(context):
                        applicable_sources.append(source)
                except Exception as exc:
                    logger.warning("Error checking applies_to for %s: %s", name, exc)

        async def _run_source(src: EvidenceSourcePort) -> tuple[list[EvidenceItem], SourceDiagnostic]:
            cb = self._circuit_breakers[src.name.lower()]
            if cb.is_open():
                return [], SourceDiagnostic(
                    url=f"source:{src.name}",
                    outcome="circuit_breaker_open",
                    bytes_fetched=0,
                    fields_extracted=[],
                    error_details=f"Source {src.name} circuit breaker is open (3 consecutive failures)",
                )

            async with self._semaphore:
                try:
                    items, diag_dict = await src.collect(context)
                    outcome = diag_dict.get("outcome", "ok")
                    if outcome == "ok":
                        cb.record_success()
                    elif outcome.startswith("http_error:5") or outcome == "timeout":
                        cb.record_failure()

                    diagnostic = SourceDiagnostic(
                        url=f"source:{src.name}",
                        outcome=outcome,
                        bytes_fetched=diag_dict.get("bytes_fetched", 0),
                        fields_extracted=diag_dict.get("fields_extracted", []),
                        error_details=diag_dict.get("error_details"),
                    )
                    return items, diagnostic
                except Exception as exc:
                    cb.record_failure()
                    logger.error("Evidence source %s failed: %s", src.name, exc, exc_info=True)
                    return [], SourceDiagnostic(
                        url=f"source:{src.name}",
                        outcome="http_error:unexpected",
                        bytes_fetched=0,
                        fields_extracted=[],
                        error_details=str(exc),
                    )

        results = await asyncio.gather(*[_run_source(s) for s in applicable_sources])
        for items, diag in results:
            all_items.extend(items)
            diagnostics.append(diag)

        return all_items, diagnostics
