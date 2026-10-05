"""Integration tests for Founder Profiles HTTP API endpoints and authentication guards."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings

settings = get_settings()
ADMIN_HEADERS = {"X-API-Key": settings.IMPORT_API_KEY}


@pytest.mark.asyncio
async def test_founder_api_public_read_endpoints(client: AsyncClient) -> None:
    # GET /api/v1/founders is accessible without authentication in public read mode
    resp = await client.get("/api/v1/founders")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)

    # 404 for nonexistent profile without auth
    resp_404 = await client.get("/api/v1/founders/nonexistent-slug")
    assert resp_404.status_code == 404


@pytest.mark.asyncio
async def test_founder_api_create_and_auth_guards(client: AsyncClient) -> None:
    payload = {
        "founder_name": "Asha Example",
        "company_name": "Example Corp",
        "evidence_text": "Asha Example\nCEO at Example Corp\nExperience:\nCEO, Example Corp (2022 - Present)",
        "notes": "Test seed profile",
    }

    # 1. POST without auth returns 401
    resp_unauth = await client.post("/api/v1/founders", json=payload)
    assert resp_unauth.status_code == 401

    # 2. POST with wrong key returns 401
    resp_wrong = await client.post(
        "/api/v1/founders",
        json=payload,
        headers={"X-API-Key": "invalid-key-32-chars-long-00000000"},
    )
    assert resp_wrong.status_code == 401

    # 3. POST with admin key succeeds (201 Created)
    resp = await client.post("/api/v1/founders", json=payload, headers=ADMIN_HEADERS)
    assert resp.status_code == 201
    created = resp.json()
    assert created["founder_name"] == "Asha Example"
    assert created["company_name"] == "Example Corp"
    assert created["slug"] == "asha-example-example-corp"
    assert created["identity_status"] == "user_asserted"
    assert created["has_previous_version"] is False

    # 4. Duplicate POST returns 409 with existing profile slug and id
    resp_dup = await client.post("/api/v1/founders", json=payload, headers=ADMIN_HEADERS)
    assert resp_dup.status_code == 409
    dup_data = resp_dup.json()
    assert dup_data["existing_slug"] == "asha-example-example-corp"
    assert dup_data["existing_id"] == created["id"]


@pytest.mark.asyncio
async def test_founder_lifecycle_crud_versioning_and_guarded_deletion(
    client: AsyncClient,
) -> None:
    # 1. Create
    create_payload = {
        "founder_name": "John Fictional",
        "company_name": "Fictional Innovations",
        "evidence_text": "John Fictional\nCTO at Fictional Innovations\nExperience:\nCTO, Fictional Innovations (2021 - 2023)",
    }
    resp_create = await client.post("/api/v1/founders", json=create_payload, headers=ADMIN_HEADERS)
    assert resp_create.status_code == 201
    slug = resp_create.json()["slug"]

    # 2. Public Read by slug
    resp_get = await client.get(f"/api/v1/founders/{slug}")
    assert resp_get.status_code == 200
    assert resp_get.json()["slug"] == slug
    assert len(resp_get.json()["experience_timeline"]) == 1

    # 3. Update without admin key -> 401
    update_payload = {
        "evidence_text": "John Fictional\nCTO at Fictional Innovations\nExperience:\nCTO, Fictional Innovations (2021 - Present)\nLead Architect, Prior Corp (2017 - 2021)",
        "notes": "Updated timeline",
    }
    resp_up_unauth = await client.put(f"/api/v1/founders/{slug}", json=update_payload)
    assert resp_up_unauth.status_code == 401

    # 4. Update with admin key -> 200, creates snapshot
    resp_up = await client.put(
        f"/api/v1/founders/{slug}", json=update_payload, headers=ADMIN_HEADERS
    )
    assert resp_up.status_code == 200
    updated = resp_up.json()
    assert len(updated["experience_timeline"]) == 2
    assert updated["has_previous_version"] is True
    assert updated["notes"] == "Updated timeline"

    # 5. Restore previous version
    resp_restore = await client.post(f"/api/v1/founders/{slug}/restore", headers=ADMIN_HEADERS)
    assert resp_restore.status_code == 200
    restored = resp_restore.json()
    assert len(restored["experience_timeline"]) == 1
    assert restored["has_previous_version"] is False

    # 6. Subsequent restore fails with 400
    resp_restore_again = await client.post(f"/api/v1/founders/{slug}/restore", headers=ADMIN_HEADERS)
    assert resp_restore_again.status_code == 400

    # 7. Canonical export (accessible with public read)
    resp_export = await client.get(f"/api/v1/founders/{slug}/export")
    assert resp_export.status_code == 200
    export_data = resp_export.json()
    assert export_data["$schema"] == "https://vset.dev/schemas/founder-profile.v1.json"
    assert export_data["slug"] == slug

    # 8. Guarded deletion: without auth -> 401
    resp_del_unauth = await client.delete(f"/api/v1/founders/{slug}?confirm={slug}")
    assert resp_del_unauth.status_code == 401

    # 9. Guarded deletion: with wrong confirmation slug -> 400
    resp_del_wrong = await client.delete(
        f"/api/v1/founders/{slug}?confirm=wrong-slug", headers=ADMIN_HEADERS
    )
    assert resp_del_wrong.status_code == 400

    # 10. Guarded deletion: with matching confirmation slug -> 200
    resp_del = await client.delete(
        f"/api/v1/founders/{slug}?confirm={slug}", headers=ADMIN_HEADERS
    )
    assert resp_del.status_code == 200
    assert resp_del.json()["deleted"] is True

    # 11. Profile is permanently deleted
    resp_gone = await client.get(f"/api/v1/founders/{slug}")
    assert resp_gone.status_code == 404


@pytest.mark.asyncio
async def test_fetch_endpoint_auth_guard(client: AsyncClient) -> None:
    fetch_payload = {
        "founder_name": "Asha Example",
        "linkedin_url": "https://www.linkedin.com/in/asha-example",
        "company_name": "Example Corp",
        "save_as_pending": False,
    }

    # Fetch without admin key -> 401
    resp_unauth = await client.post("/api/v1/founders/fetch", json=fetch_payload)
    assert resp_unauth.status_code == 401
