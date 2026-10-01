# ADR 002: Search Fallback Strategy & Resilience

## Status
Accepted

## Context
External search engines (Google, Bing) enforce bot mitigation and aggressive CAPTCHA challenges against unauthenticated scrapers. Commercial search APIs (SerpAPI, Brave, Tavily) require credit cards and per-query fees. The system must operate without paid APIs while remaining resilient against rate-limiting.

## Decision
Implement a composite search adapter (`FallbackSearchAdapter`) behind `WebSearchPort` that tries an ordered chain of search providers, each isolated by an independent `CircuitBreaker` with jittered exponential backoff:

1. **SearXNG** (`SearXNGSearchAdapter`):
   - Optional, self-hosted on the office workstation alongside Ollama.
   - Accessed via a private Tailscale tunnel (`SEARXNG_BASE_URL=http://100.x.x.x:8888`).
   - Zero rate limits, no API keys, privacy-respecting metasearch.

2. **DuckDuckGo** (`DuckDuckGoSearchAdapter`):
   - Free, no-API-key search via `duckduckgo_search`.
   - Politeness throttle: 3–5 seconds between requests, results cached via `InMemoryTtlCache` for 1 hour.

3. **Manual URL Overrides**:
   - If all automated search providers fail (or their circuits trip), the backend returns a typed `SearchUnavailableError`.
   - The frontend wizard gracefully alerts the user with "Search service currently unavailable" and invites them to paste the direct company and LinkedIn URLs.

## Consequences
- High resilience: temporary outages on public search do not block report generation.
- No commercial API costs or recurring subscriptions required.
- Clear error propagation and graceful UI degradation.
