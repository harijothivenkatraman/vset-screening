import copy
import pytest
from httpx import AsyncClient

from app.config import get_settings

settings = get_settings()


@pytest.mark.asyncio
async def test_contract_third_fake_company_no_code_change(
    client: AsyncClient,
    terraspark_json,
):
    # Construct a 3rd distinct company from the canonical schema
    third_company_json = copy.deepcopy(terraspark_json)

    # Modify company metadata
    third_company_json["canonical"]["meta"]["canonical_screen_id"] = "cs_novaorbit_998877665544"
    third_company_json["canonical"]["meta"]["company_name"] = "NovaOrbit Dynamics"
    third_company_json["canonical"]["meta"]["final_fingerprint"] = "novaorbit_fingerprint_unique_12345"
    third_company_json["canonical"]["meta"]["website"] = "www.novaorbit.space"
    third_company_json["canonical"]["content"]["cover"]["company_name"] = "NovaOrbit Dynamics"
    third_company_json["canonical"]["content"]["cover"]["website"] = "www.novaorbit.space"

    # Add a unique block variant inside the first section (e.g. custom table or unknown block fallback)
    custom_block = [
        "future_custom_block",
        "Orbital Propulsion Matrix",
        {"thrust": "120kN", "isp": "450s", "propellant": "Liquid Methane"},
    ]
    third_company_json["canonical"]["content"]["sections"][0]["blocks"].append(custom_block)

    # Import via POST /api/v1/reports/import
    import_resp = await client.post(
        "/api/v1/reports/import",
        json=third_company_json,
        headers={"X-API-Key": settings.IMPORT_API_KEY},
    )
    assert import_resp.status_code == 200
    import_data = import_resp.json()
    assert import_data["status"] == "created"
    assert import_data["company_slug"] == "novaorbit-dynamics"

    # Verify company is now in the listing
    list_resp = await client.get("/api/v1/companies")
    assert list_resp.status_code == 200
    slugs = [c["slug"] for c in list_resp.json()["companies"]]
    assert "novaorbit-dynamics" in slugs

    # Verify header
    header_resp = await client.get("/api/v1/companies/novaorbit-dynamics")
    assert header_resp.status_code == 200
    assert header_resp.json()["name"] == "NovaOrbit Dynamics"

    # Verify sections navigation
    sections_resp = await client.get("/api/v1/companies/novaorbit-dynamics/sections")
    assert sections_resp.status_code == 200
    sections = sections_resp.json()["sections"]
    assert len(sections) == 7

    # Verify section 0 contains the custom block
    sec0_resp = await client.get("/api/v1/companies/novaorbit-dynamics/sections/company")
    assert sec0_resp.status_code == 200
    sec0_blocks = sec0_resp.json()["blocks"]
    # Check that our custom block was preserved and served without errors
    assert any(b[0] == "future_custom_block" for b in sec0_blocks)

    # Verify Actions (Tab 8) and Sources (Tab 9)
    actions_resp = await client.get("/api/v1/companies/novaorbit-dynamics/actions")
    assert actions_resp.status_code == 200
    assert len(actions_resp.json()["questions"]) > 0

    sources_resp = await client.get("/api/v1/companies/novaorbit-dynamics/sources")
    assert sources_resp.status_code == 200
    assert len(sources_resp.json()["sources"]) > 0
