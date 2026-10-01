"""Search infrastructure package."""
from app.infrastructure.discovery.search.circuit_breaker import CircuitBreaker, CircuitState
from app.infrastructure.discovery.search.duckduckgo_search import DuckDuckGoSearchAdapter
from app.infrastructure.discovery.search.fallback_search import FallbackSearchAdapter
from app.infrastructure.discovery.search.searxng_search import SearXNGSearchAdapter

__all__ = [
    "CircuitBreaker",
    "CircuitState",
    "DuckDuckGoSearchAdapter",
    "FallbackSearchAdapter",
    "SearXNGSearchAdapter",
]
