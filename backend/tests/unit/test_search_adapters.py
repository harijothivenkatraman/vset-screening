"""Unit tests for search adapters."""
from __future__ import annotations

from unittest.mock import MagicMock, patch
import httpx
import pytest

from app.application.ports.web_search_port import WebSearchPort
from app.domain.entities.discovery import SearchResult
from app.domain.exceptions import SearchUnavailableError
from app.infrastructure.discovery.search.circuit_breaker import CircuitBreaker
from app.infrastructure.discovery.search.duckduckgo_search import DuckDuckGoSearchAdapter
from app.infrastructure.discovery.search.fallback_search import FallbackSearchAdapter
from app.infrastructure.discovery.search.searxng_search import SearXNGSearchAdapter


class TestDuckDuckGoSearchAdapter:
    async def test_empty_query_returns_empty(self) -> None:
        adapter = DuckDuckGoSearchAdapter()
        assert await adapter.search("") == []
        assert await adapter.search("   ") == []

    @patch("duckduckgo_search.DDGS")
    async def test_successful_search_maps_results(self, mock_ddgs_cls: MagicMock) -> None:
        mock_instance = MagicMock()
        mock_instance.text.return_value = [
            {
                "title": "Acme Corp | LinkedIn",
                "href": "https://www.linkedin.com/company/acme",
                "body": "Official LinkedIn company page.",
            },
            {
                "title": "Acme Tech",
                "href": "https://acme.io/about",
                "body": "Acme official site.",
            },
        ]
        mock_ddgs_cls.return_value.__enter__.return_value = mock_instance

        adapter = DuckDuckGoSearchAdapter()
        results = await adapter.search("Acme Corp LinkedIn", max_results=2)

        assert len(results) == 2
        assert results[0].url == "https://www.linkedin.com/company/acme"
        assert results[0].domain == "www.linkedin.com"
        assert results[0].title == "Acme Corp | LinkedIn"
        assert results[1].domain == "acme.io"


class TestSearXNGSearchAdapter:
    async def test_missing_base_url_raises(self) -> None:
        adapter = SearXNGSearchAdapter(base_url="")
        with pytest.raises(ValueError, match="not configured"):
            await adapter.search("test")

    async def test_successful_query(self) -> None:
        mock_response = {
            "results": [
                {
                    "url": "https://acme.org",
                    "title": "Acme Org",
                    "content": "Non-profit organization.",
                }
            ]
        }

        async def _mock_get(*args, **kwargs):
            return httpx.Response(200, json=mock_response, request=httpx.Request("GET", "http://test"))

        adapter = SearXNGSearchAdapter(base_url="http://100.64.0.5:8888")
        with patch.object(httpx.AsyncClient, "get", side_effect=_mock_get):
            results = await adapter.search("Acme Org")
            assert len(results) == 1
            assert results[0].url == "https://acme.org"
            assert results[0].title == "Acme Org"
            assert results[0].domain == "acme.org"


class TestFallbackSearchAdapter:
    async def test_first_provider_succeeds(self) -> None:
        p1 = MagicMock(spec=WebSearchPort)
        p1.search.return_value = [SearchResult("http://a.com", "A", "desc", "a.com")]
        p2 = MagicMock(spec=WebSearchPort)

        adapter = FallbackSearchAdapter([("p1", p1), ("p2", p2)])
        res = await adapter.search("query")
        assert len(res) == 1
        assert res[0].url == "http://a.com"
        p2.search.assert_not_called()

    async def test_first_fails_fallback_to_second(self) -> None:
        p1 = MagicMock(spec=WebSearchPort)
        p1.search.side_effect = RuntimeError("p1 rate limited")
        p2 = MagicMock(spec=WebSearchPort)
        p2.search.return_value = [SearchResult("http://b.com", "B", "desc", "b.com")]

        cb1 = CircuitBreaker("p1", max_retries=0)
        cb2 = CircuitBreaker("p2", max_retries=0)

        adapter = FallbackSearchAdapter(
            [("p1", p1), ("p2", p2)],
            circuit_breakers={"p1": cb1, "p2": cb2},
        )
        res = await adapter.search("query")
        assert len(res) == 1
        assert res[0].url == "http://b.com"

    async def test_all_fail_raises_search_unavailable(self) -> None:
        p1 = MagicMock(spec=WebSearchPort)
        p1.search.side_effect = RuntimeError("p1 down")
        p2 = MagicMock(spec=WebSearchPort)
        p2.search.side_effect = RuntimeError("p2 down")

        cb1 = CircuitBreaker("p1", max_retries=0)
        cb2 = CircuitBreaker("p2", max_retries=0)

        adapter = FallbackSearchAdapter(
            [("p1", p1), ("p2", p2)],
            circuit_breakers={"p1": cb1, "p2": cb2},
        )

        with pytest.raises(SearchUnavailableError) as exc_info:
            await adapter.search("query")

        assert exc_info.value.providers_tried == ["p1", "p2"]
