"""Domain entities for the Company Discovery feature.

Pure value objects and entities — no framework dependencies.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class JobState(Enum):
    """State machine for discovery jobs.
    
    Allowed transitions:
        QUEUED → RUNNING
        RUNNING → SUCCEEDED | PARTIAL | FAILED
    """
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"       # completed with warnings (some sources failed)
    FAILED = "failed"


@dataclass(frozen=True)
class SearchResult:
    """A single result from a web search."""
    url: str
    title: str
    snippet: str
    domain: str


@dataclass(frozen=True)
class SourceCandidate:
    """A candidate match from web search, scored by relevance."""
    url: str
    title: str
    snippet: str
    domain: str
    confidence: float          # 0.0–1.0
    category: str              # "company_linkedin", "founder_linkedin", "website", "news"
    search_query: str
    entity_name: str           # the name we searched for


@dataclass(frozen=True)
class CompanyProfile:
    """Scraped public LinkedIn company profile data."""
    name: str | None = None
    description: str | None = None
    industry: str | None = None
    company_size: str | None = None
    headquarters: str | None = None
    website: str | None = None
    founded_year: str | None = None
    specialties: list[str] = field(default_factory=list)
    followers: int | None = None
    logo_url: str | None = None
    tagline: str | None = None
    url: str = ""
    retrieved_at: str = ""
    is_auth_walled: bool = False
    raw_json_ld: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PersonProfile:
    """Scraped public LinkedIn person profile data."""
    name: str | None = None
    headline: str | None = None
    location: str | None = None
    summary: str | None = None
    education: list[dict[str, str]] = field(default_factory=list)
    experience: list[dict[str, str]] = field(default_factory=list)
    follower_count: int | None = None
    connection_count: int | None = None
    avatar_url: str | None = None
    url: str = ""
    retrieved_at: str = ""
    is_auth_walled: bool = False
    raw_json_ld: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PageContent:
    """Fetched and extracted web page content."""
    url: str
    title: str
    description: str
    text: str                  # main text content, stripped of nav/ads
    og_tags: dict[str, str] = field(default_factory=dict)
    retrieved_at: str = ""
    content_type: str = "text/html"
    status_code: int = 200


@dataclass(frozen=True)
class EvidenceSource:
    """A source used in evidence collection, for the source register."""
    source_id: str             # "src_xxxx" format
    url: str
    publisher: str
    title: str | None = None
    published_date: str | None = None
    source_type: str = "WEB"   # WEB, SOCIAL_MEDIA, NEWS, COMPANY_WEBSITE
    retrieved_at: str = ""


@dataclass
class Evidence:
    """Collected evidence from all sources for a discovery job."""
    company_profile: CompanyProfile | None = None
    founder_profiles: list[PersonProfile] = field(default_factory=list)
    website_pages: list[PageContent] = field(default_factory=list)
    news_articles: list[PageContent] = field(default_factory=list)
    sources: list[EvidenceSource] = field(default_factory=list)


@dataclass
class DiscoveryJob:
    """Mutable entity tracking job progress. Not frozen because state changes."""
    id: str
    company_name: str
    founder_names: list[str]
    state: JobState
    stage: str                 # current stage label for the UI
    progress: float            # 0.0–1.0
    warnings: list[str]
    result_slug: str | None
    created_at: datetime
    updated_at: datetime
    confirmed_urls: dict[str, str]   # category → URL
    error_message: str | None = None

    def transition_to(self, new_state: JobState) -> None:
        """Enforce state machine transitions."""
        allowed: dict[JobState, set[JobState]] = {
            JobState.QUEUED: {JobState.RUNNING},
            JobState.RUNNING: {JobState.SUCCEEDED, JobState.PARTIAL, JobState.FAILED},
        }
        if new_state not in allowed.get(self.state, set()):
            raise ValueError(
                f"Invalid state transition: {self.state.value} → {new_state.value}"
            )
        self.state = new_state
        self.updated_at = datetime.now()

    def update_progress(self, stage: str, progress: float) -> None:
        self.stage = stage
        self.progress = min(max(progress, 0.0), 1.0)
        self.updated_at = datetime.now()

    def add_warning(self, warning: str) -> None:
        self.warnings.append(warning)
        self.updated_at = datetime.now()


def generate_content_fingerprint(content: str) -> str:
    """Generate a SHA-256 fingerprint for content change detection."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def generate_source_id(url: str) -> str:
    """Generate a deterministic source ID from a URL."""
    h = hashlib.md5(url.encode("utf-8")).hexdigest()[:12]
    return f"src_{h}"


def generate_screen_id(company_name: str) -> str:
    """Generate a deterministic canonical screen ID from company name."""
    h = hashlib.sha256(company_name.lower().strip().encode("utf-8")).hexdigest()[:24]
    return f"cs_{h}"
