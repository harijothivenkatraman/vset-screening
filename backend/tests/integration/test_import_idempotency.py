import copy

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.ingestion.import_service import ReportImportService


@pytest.mark.asyncio
async def test_import_idempotency_workflow(db_session: AsyncSession, terraspark_json):
    service = ReportImportService(db_session)

    # 1. First import -> status "created"
    res1 = await service.import_report(terraspark_json)
    assert res1.status == "created"
    assert res1.company_slug == "terraspark"

    # 2. Re-import same data -> status "unchanged" (idempotent)
    res2 = await service.import_report(terraspark_json)
    assert res2.status == "unchanged"
    assert res2.company_slug == "terraspark"

    # 3. Import with modified fingerprint -> status "updated"
    modified_json = copy.deepcopy(terraspark_json)
    modified_json["canonical"]["meta"]["final_fingerprint"] = "new_fingerprint_abc123"
    modified_json["canonical"]["content"]["cover"]["company_name"] = "TerraSpark Global"

    res3 = await service.import_report(modified_json)
    assert res3.status == "updated"
    assert res3.company_slug == "terraspark"

    # 4. Re-import modified data -> status "unchanged" again
    res4 = await service.import_report(modified_json)
    assert res4.status == "unchanged"
