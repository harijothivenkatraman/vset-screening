"""Integration tests for discovery API endpoints, auth guards, background jobs, and image proxy."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch
import httpx
import pytest

from app.application.ports.web_search_port import WebSearchPort
from app.config import get_settings
from app.domain.entities.discovery import CompanyProfile, SearchResult
from app.presentation.dependencies import (
    get_profile_scraper_port,
    get_web_search_port,
)
from app.main import app
from tests.fakes.fake_ports import FakeProfileScraper, FakeWebSearch

settings = get_settings()
AUTH_HEADERS = {"X-API-Key": settings.IMPORT_API_KEY}


class TestDiscoveryApiAuthGuards:
    async def test_resolve_requires_auth(self, client: httpx.AsyncClient) -> None:
        resp = await client.post("/api/v1/discovery/resolve", json={"company_name": "Test", "founder_names": ["Alice"]})
        assert resp.status_code == 401

    async def test_jobs_requires_auth(self, client: httpx.AsyncClient) -> None:
        resp = await client.post("/api/v1/discovery/jobs", json={"company_name": "Test", "founder_names": ["Alice"]})
        assert resp.status_code == 401

    async def test_job_status_requires_auth(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/api/v1/discovery/jobs/nonexistent")
        assert resp.status_code == 401

    async def test_health_is_public(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/api/v1/discovery/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "discovery_enabled" in data
        assert "free_disk_gb" in data


class TestResolveCandidatesEndpoint:
    async def test_resolve_success(self, client: httpx.AsyncClient) -> None:
        fake_search = FakeWebSearch(results=[
            SearchResult(
                url="https://linkedin.com/company/nexus-ai",
                title="Nexus AI | LinkedIn",
                snippet="Autonomous intelligence platform.",
                domain="linkedin.com",
            ),
        ])

        app.dependency_overrides[get_web_search_port] = lambda: fake_search
        try:
            resp = await client.post(
                "/api/v1/discovery/resolve",
                headers=AUTH_HEADERS,
                json={
                    "company_name": "Nexus AI",
                    "founder_names": ["David Chen"],
                    "website_override": "https://nexus.ai",
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert not data["search_unavailable"]
            assert "company_linkedin" in data["candidates"]
            assert "website" in data["candidates"]
            assert data["candidates"]["website"][0]["url"] == "https://nexus.ai"
        finally:
            app.dependency_overrides.pop(get_web_search_port, None)


class TestDiscoveryJobLifecycle:
    async def test_job_enqueue_and_execution(self, client: httpx.AsyncClient) -> None:
        fake_scraper = FakeProfileScraper()
        fake_scraper.company_profiles["https://linkedin.com/company/orbit"] = CompanyProfile(
            name="Orbit Systems",
            description="Satellite communications.",
            industry="Aerospace",
        )

        app.dependency_overrides[get_profile_scraper_port] = lambda: fake_scraper
        try:
            # 1. Enqueue job (202 Accepted)
            resp = await client.post(
                "/api/v1/discovery/jobs",
                headers=AUTH_HEADERS,
                json={
                    "company_name": "Orbit Systems",
                    "founder_names": ["Elena Vance"],
                    "confirmed_urls": {
                        "company_linkedin": "https://linkedin.com/company/orbit",
                    },
                },
            )
            assert resp.status_code == 202
            data = resp.json()
            job_id = data["job_id"]
            assert data["state"] == "queued"

            # 2. Poll job status
            poll_resp = await client.get(
                f"/api/v1/discovery/jobs/{job_id}",
                headers=AUTH_HEADERS,
            )
            assert poll_resp.status_code == 200
            status_data = poll_resp.json()
            assert status_data["job_id"] == job_id
            assert status_data["company_name"] == "Orbit Systems"
            assert status_data["state"] in ("queued", "running", "succeeded", "partial")

            # 3. Verify company is listed in API once completed
            if status_data["result_slug"]:
                comp_resp = await client.get("/api/v1/companies")
                assert comp_resp.status_code == 200
                slugs = [c["slug"] for c in comp_resp.json()["companies"]]
                assert status_data["result_slug"] in slugs
        finally:
            app.dependency_overrides.pop(get_profile_scraper_port, None)


class TestImageProxyEndpoint:
    async def test_disallowed_host_returns_403(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/api/v1/image-proxy?url=https://evil-site.com/avatar.jpg")
        assert resp.status_code == 403
        assert "not in the allowed image proxy hosts" in resp.json()["detail"]

    async def test_internal_ip_returns_400(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/api/v1/image-proxy?url=http://127.0.0.1/logo.png")
        assert resp.status_code == 403 or resp.status_code == 400

    async def test_allowed_host_streams_image(self, client: httpx.AsyncClient) -> None:
        mock_image_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"

        class MockImageStream:
            status_code = 200
            headers = {"content-type": "image/png"}

            async def send(self, *args, **kwargs):
                return self

            async def aiter_bytes(self):
                yield mock_image_bytes

            async def aclose(self):
                pass

        mock_client = AsyncMock()
        mock_client.build_request.return_value = "req"
        mock_client.send.return_value = MockImageStream()
        mock_client.aclose = AsyncMock()

        with patch("httpx.AsyncClient", return_value=mock_client):
            resp = await client.get("/api/v1/image-proxy?url=https://media.licdn.com/dms/image/v2/avatar.png")
            assert resp.status_code == 200
            assert resp.headers.get("content-type") == "image/png"
            assert resp.content == mock_image_bytes
