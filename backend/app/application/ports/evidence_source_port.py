"""Port defining the open/closed EvidenceSource contract for multi-source evidence collection."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ReliabilityTier(str, Enum):
    OFFICIAL = "OFFICIAL"         # Government/regulatory, RDAP, authoritative domain
    HIGH = "HIGH"                 # Company official website, verified publications
    MEDIUM = "MEDIUM"             # Mainstream news, GDELT, Wikidata
    LOW = "LOW"                   # Aggregators, snippets, web archives
    UNVERIFIED = "UNVERIFIED"     # User supplied or uncorroborated


@dataclass(frozen=True)
class ExtractedField:
    """An individual extracted attribute with supporting evidence."""
    field_name: str               # e.g. "founded_year", "headquarters", "stage", "funding_rounds"
    value: Any                    # parsed value
    exact_quote: str              # exact supporting quote from source
    confidence: float = 1.0


@dataclass(frozen=True)
class EvidenceItem:
    """Standardized multi-source evidence item."""
    source_id: str                # unique id, e.g. "src_rdap_mysa_io"
    source_type: str              # REGISTRY, COMPANY_WEBSITE, NEWS, WEB, USER_SUPPLIED
    url: str
    retrieved_at: str
    extracted_fields: list[ExtractedField]
    excerpt: str                  # brief text excerpt / snippet
    publisher: str = ""
    title: str = ""


@dataclass(frozen=True)
class DiscoveryContext:
    """Context passed to evidence sources."""
    company_name: str
    founder_names: list[str] = field(default_factory=list)
    website_url: str | None = None
    confirmed_urls: dict[str, str] = field(default_factory=dict)
    job_id: str = ""
    domain: str = ""


class EvidenceSourcePort(ABC):
    """Port interface for multi-source evidence collection plugins (Open/Closed)."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Identifier for the source (e.g. 'rdap', 'wikidata', 'news', 'wayback')."""
        ...

    @property
    @abstractmethod
    def reliability_tier(self) -> ReliabilityTier:
        """Reliability rating of this source."""
        ...

    @property
    @abstractmethod
    def fields_supported(self) -> list[str]:
        """Fields this source can supply (e.g. ['founded_year', 'stage', 'funding_rounds'])."""
        ...

    @abstractmethod
    async def applies_to(self, context: DiscoveryContext) -> bool:
        """Check if source is relevant/applicable to the given context."""
        ...

    @abstractmethod
    async def collect(
        self, context: DiscoveryContext
    ) -> tuple[list[EvidenceItem], dict[str, Any]]:
        """Collect evidence items and return (items, diagnostic_dict).
        
        diagnostic_dict must contain:
        - outcome: str (ok | http_error:<code> | empty_text | parse_empty | timeout | blocked)
        - bytes_fetched: int
        - fields_extracted: list[str]
        - error_details: str | None
        """
        ...


class EvidenceRegistryPort(ABC):
    """Port interface for registry collecting evidence across sources."""

    @abstractmethod
    async def collect_all(
        self, context: DiscoveryContext
    ) -> tuple[list[EvidenceItem], list[Any]]:
        """Run all enabled and applicable sources, returning (items, diagnostics)."""
        ...

