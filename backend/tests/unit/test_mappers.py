from uuid import uuid4

from app.application.mappers.action_mapper import map_action_items_from_raw
from app.application.mappers.report_meta_mapper import (
    generate_slug,
    map_company_from_raw,
    map_report_from_raw,
)
from app.application.mappers.section_mapper import map_sections_from_raw
from app.application.mappers.source_mapper import map_sources_from_raw


def test_generate_slug():
    assert generate_slug("TerraSpark") == "terraspark"
    assert generate_slug("Mysa") == "mysa"
    assert generate_slug("Super AI Inc. (2026)") == "super-ai-inc-2026"
    assert generate_slug("  Leading Edge Tech  ") == "leading-edge-tech"


def test_map_company_from_raw(terraspark_json):
    company = map_company_from_raw(terraspark_json)
    assert company.name == "TerraSpark"
    assert company.slug == "terraspark"
    assert company.website == "www.terraspark.energy"


def test_map_report_from_raw(terraspark_json):
    company_id = uuid4()
    report = map_report_from_raw(terraspark_json, company_id=company_id)
    assert report.company_id == company_id
    assert report.canonical_screen_id == "cs_f2a8fd552eed7f7db99bc699"
    assert report.version == "V1"
    assert report.canonical_version == "commercial-screen-canonical.2"
    assert report.schema_version == "vset.screen.v2"
    assert report.audience == "FOUNDER"
    assert report.audience_label == "Founder Screen"
    assert len(report.ribbon) == 5


def test_map_sections_from_raw(terraspark_json):
    report_id = uuid4()
    sections = map_sections_from_raw(terraspark_json, report_id=report_id)
    assert len(sections) == 7
    keys = [s.key for s in sections]
    assert keys == ["company", "team", "product", "validation", "market", "competition", "funding"]
    for idx, s in enumerate(sections):
        assert s.position == idx
        assert s.report_id == report_id
        assert len(s.blocks) > 0


def test_map_action_items_from_raw(terraspark_json):
    report_id = uuid4()
    actions = map_action_items_from_raw(terraspark_json, report_id=report_id)
    kinds = {a.kind for a in actions}
    assert "SECTION_REQUEST" in kinds
    assert "DD_QUESTION" in kinds
    assert "DD_DOCUMENT" in kinds

    # Verify SECTION_REQUEST items have 'where' matching section titles
    section_requests = [a for a in actions if a.kind == "SECTION_REQUEST"]
    assert len(section_requests) > 0
    assert any(a.where == "Key facts & context" for a in section_requests)


def test_map_sources_from_raw(terraspark_json):
    report_id = uuid4()
    sources = map_sources_from_raw(terraspark_json, report_id=report_id)
    assert len(sources) == 9
    assert sources[0].source_id == "src_13c9788a6c34"
    assert sources[0].publisher == "tech.eu"
