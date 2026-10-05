"""Integration tests for company deletion endpoint: cascade deletion, ?confirm=<slug> check, and PII absence."""
from __future__ import annotations

import copy
from typing import Any
import pytest
from httpx import AsyncClient
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.infrastructure.ingestion.import_service import ReportImportService
from app.infrastructure.persistence.models import (
    CompanyModel,
    ReportModel,
    SectionModel,
    ActionItemModel,
    SourceModel,
    RawSnapshotModel,
)

settings = get_settings()
AUTH_HEADERS = {"X-API-Key": settings.IMPORT_API_KEY}


@pytest.mark.asyncio
async def test_company_delete_requires_auth(client: AsyncClient) -> None:
    # Without auth header -> 401 or 403 depending on security settings
    resp = await client.delete("/api/v1/companies/mysa?confirm=mysa")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_company_delete_requires_matching_confirm(
    db_session: AsyncSession,
    client: AsyncClient,
    mysa_json: dict[str, Any],
) -> None:
    importer = ReportImportService(db_session)
    await importer.import_report(mysa_json)

    # Missing confirm param -> 422 or 400
    resp1 = await client.delete("/api/v1/companies/mysa", headers=AUTH_HEADERS)
    assert resp1.status_code in (400, 422)

    # Mismatched confirm param -> 400
    resp2 = await client.delete("/api/v1/companies/mysa?confirm=wrong-slug", headers=AUTH_HEADERS)
    assert resp2.status_code == 400
    assert "must match company slug" in resp2.json()["detail"]


@pytest.mark.asyncio
async def test_company_delete_cascade_and_pii_absence_sqlite(
    db_session: AsyncSession,
    client: AsyncClient,
    mysa_json: dict[str, Any],
) -> None:
    # 1. Prepare payload with intentional PII inserted in audit snapshots
    payload = copy.deepcopy(mysa_json)
    secret_email = "supersecret_founder_pii@example.com"
    secret_phone = "+1 (555) 987-6543"

    # Insert into raw snapshot
    if "raw_snapshot" not in payload:
        payload["raw_snapshot"] = {}
    payload["raw_snapshot"]["founder_notes"] = f"Contact email: {secret_email}, phone: {secret_phone}"

    importer = ReportImportService(db_session)
    await importer.import_report(payload)

    # Verify company exists
    get_resp = await client.get("/api/v1/companies/mysa")
    assert get_resp.status_code == 200

    # Verify PII was sanitized from DB raw snapshot on import
    raw_stmt = select(RawSnapshotModel)
    raw_res = await db_session.execute(raw_stmt)
    snapshots = raw_res.scalars().all()
    assert len(snapshots) >= 1
    for s in snapshots:
        raw_str = str(s.raw_json)
        assert secret_email not in raw_str, "Email PII must be scrubbed upon ingestion"
        assert secret_phone not in raw_str, "Phone PII must be scrubbed upon ingestion"

    # 2. Check counts before delete
    c_count = (await db_session.execute(select(func.count()).select_from(CompanyModel))).scalar()
    r_count = (await db_session.execute(select(func.count()).select_from(ReportModel))).scalar()
    sec_count = (await db_session.execute(select(func.count()).select_from(SectionModel))).scalar()
    act_count = (await db_session.execute(select(func.count()).select_from(ActionItemModel))).scalar()
    src_count = (await db_session.execute(select(func.count()).select_from(SourceModel))).scalar()
    raw_count = (await db_session.execute(select(func.count()).select_from(RawSnapshotModel))).scalar()

    assert c_count >= 1
    assert r_count >= 1
    assert sec_count >= 1
    assert act_count >= 1
    assert src_count >= 1
    assert raw_count >= 1

    # 3. Execute DELETE with matching confirm
    del_resp = await client.delete("/api/v1/companies/mysa?confirm=mysa", headers=AUTH_HEADERS)
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted"] is True
    assert del_resp.json()["slug"] == "mysa"

    # 4. Verify cascade deletion across all related tables
    c_after = (await db_session.execute(select(func.count()).select_from(CompanyModel).where(CompanyModel.slug == "mysa"))).scalar()
    r_after = (await db_session.execute(select(func.count()).select_from(ReportModel))).scalar()
    sec_after = (await db_session.execute(select(func.count()).select_from(SectionModel))).scalar()
    act_after = (await db_session.execute(select(func.count()).select_from(ActionItemModel))).scalar()
    src_after = (await db_session.execute(select(func.count()).select_from(SourceModel))).scalar()
    raw_after = (await db_session.execute(select(func.count()).select_from(RawSnapshotModel))).scalar()

    assert c_after == 0, "Company must be deleted"
    assert r_after == 0, "Reports must be cascade-deleted"
    assert sec_after == 0, "Sections must be cascade-deleted"
    assert act_after == 0, "Action items must be cascade-deleted"
    assert src_after == 0, "Sources must be cascade-deleted"
    assert raw_after == 0, "Raw snapshots must be cascade-deleted"

    # 5. Verify GET returns 404
    get_after = await client.get("/api/v1/companies/mysa")
    assert get_after.status_code == 404
