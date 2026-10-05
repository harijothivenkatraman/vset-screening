"""Unit tests for API key authentication and production transport security guards."""
from __future__ import annotations

import io
import pytest
from httpx import AsyncClient

from app.config import get_settings


@pytest.mark.asyncio
async def test_get_founders_works_without_key(client: AsyncClient) -> None:
    response = await client.get("/api/v1/founders")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_check_works_without_key(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200


# Write endpoint 1: POST /api/v1/founders
@pytest.mark.asyncio
async def test_post_founders_returns_401_without_key(client: AsyncClient) -> None:
    response = await client.post("/api/v1/founders", json={"founder_name": "Test Founder"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_post_founders_returns_401_with_wrong_key(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/founders",
        headers={"X-API-Key": "wrong-key"},
        json={"founder_name": "Test Founder"},
    )
    assert response.status_code == 401


# Write endpoint 2: POST /api/v1/founders/upload-pdf
@pytest.mark.asyncio
async def test_post_upload_pdf_returns_401_without_key(client: AsyncClient) -> None:
    dummy_pdf = io.BytesIO(b"%PDF-1.4 dummy content")
    response = await client.post(
        "/api/v1/founders/upload-pdf",
        data={"founder_name": "Test Founder"},
        files={"file": ("profile.pdf", dummy_pdf, "application/pdf")},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_post_upload_pdf_returns_401_with_wrong_key(client: AsyncClient) -> None:
    dummy_pdf = io.BytesIO(b"%PDF-1.4 dummy content")
    response = await client.post(
        "/api/v1/founders/upload-pdf",
        headers={"X-API-Key": "wrong-key"},
        data={"founder_name": "Test Founder"},
        files={"file": ("profile.pdf", dummy_pdf, "application/pdf")},
    )
    assert response.status_code == 401


# Write endpoint 3: POST /api/v1/founders/fetch
@pytest.mark.asyncio
async def test_post_fetch_returns_401_without_key(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/founders/fetch",
        json={"founder_name": "Test Founder", "linkedin_url": "https://linkedin.com/in/test"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_post_fetch_returns_401_with_wrong_key(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/founders/fetch",
        headers={"X-API-Key": "wrong-key"},
        json={"founder_name": "Test Founder", "linkedin_url": "https://linkedin.com/in/test"},
    )
    assert response.status_code == 401


# Write endpoint 4: POST /api/v1/founders/pending
@pytest.mark.asyncio
async def test_post_pending_returns_401_without_key(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/founders/pending",
        json={"founder_name": "Test Founder"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_post_pending_returns_401_with_wrong_key(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/founders/pending",
        headers={"X-API-Key": "wrong-key"},
        json={"founder_name": "Test Founder"},
    )
    assert response.status_code == 401


# Write endpoint 5: PUT /api/v1/founders/{id_or_slug}
@pytest.mark.asyncio
async def test_put_founder_returns_401_without_key(client: AsyncClient) -> None:
    response = await client.put("/api/v1/founders/test-slug", json={"notes": "updated"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_put_founder_returns_401_with_wrong_key(client: AsyncClient) -> None:
    response = await client.put(
        "/api/v1/founders/test-slug",
        headers={"X-API-Key": "wrong-key"},
        json={"notes": "updated"},
    )
    assert response.status_code == 401


# Write endpoint 6: POST /api/v1/founders/{id_or_slug}/restore
@pytest.mark.asyncio
async def test_post_restore_returns_401_without_key(client: AsyncClient) -> None:
    response = await client.post("/api/v1/founders/test-slug/restore")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_post_restore_returns_401_with_wrong_key(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/founders/test-slug/restore",
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 401


# Write endpoint 7: DELETE /api/v1/founders/{id_or_slug}
@pytest.mark.asyncio
async def test_delete_founder_returns_401_without_key(client: AsyncClient) -> None:
    response = await client.delete("/api/v1/founders/test-slug?confirm=test-slug")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_founder_returns_401_with_wrong_key(client: AsyncClient) -> None:
    response = await client.delete(
        "/api/v1/founders/test-slug?confirm=test-slug",
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 401


# Production plain HTTP refusal vs HTTPS / localhost
@pytest.mark.asyncio
async def test_production_refuses_admin_over_plain_http_from_remote(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    # Valid key, but over plain HTTP from a public IP -> 403 Forbidden
    response = await client.delete(
        "/api/v1/founders/test-slug?confirm=test-slug",
        headers={
            "X-API-Key": settings.IMPORT_API_KEY,
            "X-Forwarded-Proto": "http",
            "X-Forwarded-For": "203.0.113.195",
            "Host": "api.vset.example.com",
        },
    )
    assert response.status_code == 403
    assert "refused in production" in response.json().get("detail", "")


@pytest.mark.asyncio
async def test_production_permits_admin_over_https(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    response = await client.delete(
        "/api/v1/founders/test-slug?confirm=test-slug",
        headers={
            "X-API-Key": settings.IMPORT_API_KEY,
            "X-Forwarded-Proto": "https",
            "X-Forwarded-For": "203.0.113.195",
            "Host": "api.vset.example.com",
        },
    )
    # Auth passed, returns 404 because profile does not exist
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_production_permits_admin_over_localhost_tunnel(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    response = await client.delete(
        "/api/v1/founders/test-slug?confirm=test-slug",
        headers={
            "X-API-Key": settings.IMPORT_API_KEY,
            "X-Forwarded-Proto": "http",
            "X-Forwarded-For": "127.0.0.1",
            "Host": "localhost:8000",
        },
    )
    # Localhost exception applies: auth passed, returns 404
    assert response.status_code == 404
