import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.infrastructure.ingestion.import_service import ReportImportService

settings = get_settings()


@pytest.mark.asyncio
async def test_full_api_nine_tabs_for_both_companies(
    db_session: AsyncSession,
    client: AsyncClient,
    terraspark_json,
    mysa_json,
):
    importer = ReportImportService(db_session)
    await importer.import_report(terraspark_json)
    await importer.import_report(mysa_json)

    # 1. GET /api/v1/companies -> lists both companies
    resp = await client.get("/api/v1/companies")
    assert resp.status_code == 200
    companies = resp.json()["companies"]
    slugs = [c["slug"] for c in companies]
    assert "terraspark" in slugs
    assert "mysa" in slugs

    # Verify both companies have all 9 tabs served via API
    for slug in ["terraspark", "mysa"]:
        # Company Header
        header_resp = await client.get(f"/api/v1/companies/{slug}")
        assert header_resp.status_code == 200
        header_data = header_resp.json()
        assert header_data["slug"] == slug
        assert len(header_data["ribbon"]) >= 5
        assert "audienceLabel" in header_data

        # Sections Navigation (Tabs 1-7)
        nav_resp = await client.get(f"/api/v1/companies/{slug}/sections")
        assert nav_resp.status_code == 200
        sections_nav = nav_resp.json()["sections"]
        assert len(sections_nav) == 7
        section_keys = [s["key"] for s in sections_nav]

        expected_keys = [
            "company",       # Tab 1: Key facts & context
            "team",          # Tab 2: Founder & team
            "product",       # Tab 3: Product & technology
            "validation",    # Tab 4: Validation & market signals
            "market",        # Tab 5: Market opportunity
            "competition",   # Tab 6: Competitive landscape
            "funding",       # Tab 7: Funding history
        ]
        assert section_keys == expected_keys

        # Check each section (Tabs 1-7) returns blocks and informationToPrepare
        for key in expected_keys:
            sec_resp = await client.get(f"/api/v1/companies/{slug}/sections/{key}")
            assert sec_resp.status_code == 200, f"Failed for {slug} section {key}"
            sec_data = sec_resp.json()
            assert sec_data["key"] == key
            assert len(sec_data["blocks"]) > 0
            assert "informationToPrepare" in sec_data

        # Tab 8: Investor questions & information to prepare
        actions_resp = await client.get(f"/api/v1/companies/{slug}/actions")
        assert actions_resp.status_code == 200
        actions_data = actions_resp.json()
        assert "concerns" in actions_data
        assert actions_data["concerns"]["message"] == "No public concern or source conflict is recorded in this baseline."
        assert len(actions_data["questions"]) > 0  # Part A questions
        assert len(actions_data["documents"]) > 0  # Part B documents

        # Tab 9: About this screen & sources
        sources_resp = await client.get(f"/api/v1/companies/{slug}/sources")
        assert sources_resp.status_code == 200
        sources_data = sources_resp.json()
        assert len(sources_data["sources"]) > 0
        assert "aboutText" in sources_data
        assert len(sources_data["limitations"]) > 0


@pytest.mark.asyncio
async def test_import_endpoint_auth_guard(client: AsyncClient, terraspark_json):
    # Missing API key -> 401
    resp = await client.post("/api/v1/reports/import", json=terraspark_json)
    assert resp.status_code == 401

    # Invalid API key -> 401
    resp = await client.post(
        "/api/v1/reports/import",
        json=terraspark_json,
        headers={"X-API-Key": "wrong-key"},
    )
    assert resp.status_code == 401

    # Valid API key -> 200
    resp = await client.post(
        "/api/v1/reports/import",
        json=terraspark_json,
        headers={"X-API-Key": settings.IMPORT_API_KEY},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "created"
    assert resp.json()["company_slug"] == "terraspark"
