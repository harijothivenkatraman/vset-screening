"""Domain and application exception hierarchy.

These exceptions are mapped to HTTP responses in the presentation layer.
"""


class DiscoveryError(Exception):
    """Base exception for all discovery-related errors."""
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class DiscoveryDisabledError(DiscoveryError):
    """Discovery feature is disabled via configuration."""
    def __init__(self) -> None:
        super().__init__("Company Discovery is disabled. Set DISCOVERY_ENABLED=true to enable.")


class SearchUnavailableError(DiscoveryError):
    """All search providers have failed or are circuit-broken."""
    def __init__(self, providers_tried: list[str] | None = None) -> None:
        tried = ", ".join(providers_tried or [])
        msg = f"All search providers unavailable (tried: {tried}). Please provide URLs manually."
        super().__init__(msg)
        self.providers_tried = providers_tried or []


class SourceUnavailableError(DiscoveryError):
    """A specific source could not be fetched (non-fatal, becomes a warning)."""
    def __init__(self, source_url: str, reason: str) -> None:
        super().__init__(f"Source unavailable: {source_url} — {reason}")
        self.source_url = source_url
        self.reason = reason


class LowConfidenceMatchError(DiscoveryError):
    """Search returned only low-confidence matches."""
    def __init__(self, query: str, best_confidence: float) -> None:
        super().__init__(f"Low confidence match for '{query}' (best: {best_confidence:.0%})")
        self.query = query
        self.best_confidence = best_confidence


class ExtractionFailedError(DiscoveryError):
    """LLM extraction or report assembly failed."""
    def __init__(self, section: str, reason: str) -> None:
        super().__init__(f"Extraction failed for section '{section}': {reason}")
        self.section = section
        self.reason = reason


class LlmUnavailableError(DiscoveryError):
    """The configured LLM server is not reachable."""
    def __init__(self, base_url: str, reason: str = "") -> None:
        super().__init__(f"LLM server at {base_url} is unavailable: {reason}")
        self.base_url = base_url


class JobNotFoundError(DiscoveryError):
    """Discovery job not found."""
    def __init__(self, job_id: str) -> None:
        super().__init__(f"Discovery job '{job_id}' not found")
        self.job_id = job_id


class RateLimitExceededError(DiscoveryError):
    """Per-key rate limit exceeded."""
    def __init__(self, limit: int, window: str = "hour") -> None:
        super().__init__(f"Rate limit exceeded: {limit} jobs per {window}")
        self.limit = limit


class InsufficientDiskSpaceError(DiscoveryError):
    """Not enough free disk space to accept new jobs."""
    def __init__(self, available_gb: float, required_gb: float) -> None:
        super().__init__(f"Insufficient disk space: {available_gb:.1f} GB available, {required_gb:.1f} GB required")
        self.available_gb = available_gb
        self.required_gb = required_gb
