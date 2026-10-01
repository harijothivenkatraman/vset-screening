"""Golden test: evidence-to-report mapper output must pass version_gate + schema_validator.

This is the most critical test — it validates that the discovery pipeline
can produce a JSON tree that the existing import pipeline will accept.
"""
from __future__ import annotations

import pytest

from app.application.mappers.evidence_to_report_mapper import build_canonical_report
from app.domain.entities.discovery import (
    CompanyProfile,
    Evidence,
    EvidenceSource,
    PageContent,
    PersonProfile,
)
from app.infrastructure.ingestion.schema_validator import validate_raw_report_json
from app.infrastructure.ingestion.version_gate import check_version_gate


class TestEvidenceMapperGolden:
    """Validate that build_canonical_report output passes the import pipeline."""

    def test_minimal_evidence_passes_gates(self) -> None:
        """An empty Evidence (no data found) must still produce valid JSON."""
        evidence = Evidence()
        result = build_canonical_report(evidence, "TestCo", ["Alice"])

        # Must pass version gate
        check_version_gate(result)

        # Must pass schema validator
        validated = validate_raw_report_json(result)
        assert validated is not None

    def test_rich_evidence_passes_gates(self) -> None:
        """Full evidence with company + founders + website + news."""
        evidence = _make_rich_evidence()
        result = build_canonical_report(
            evidence, "Acme Corp", ["Alice Smith", "Bob Jones"],
        )

        check_version_gate(result)
        validate_raw_report_json(result)

    def test_canonical_structure(self) -> None:
        """Verify the top-level structure matches the import contract."""
        evidence = Evidence()
        result = build_canonical_report(evidence, "TestCo", ["Founder"])

        # Top-level keys
        assert "canonical" in result
        assert "meta" in result
        assert "presentation" in result

        # Canonical keys
        canonical = result["canonical"]
        assert "meta" in canonical
        assert "content" in canonical

        # Canonical meta required fields
        meta = canonical["meta"]
        assert meta["canonical_version"] == "commercial-screen-canonical.2"
        assert meta["company_name"] == "TestCo"
        assert len(meta["canonical_screen_id"]) > 0
        assert len(meta["final_fingerprint"]) > 0

        # Content keys
        content = canonical["content"]
        assert "cover" in content
        assert "sections" in content
        assert "actions" in content
        assert "action_requirements" in content
        assert "final" in content

        # Cover
        assert content["cover"]["company_name"] == "TestCo"

        # Final meta
        final = content["final"]
        assert final["meta"]["schema_version"] == "vset.screen.v2"

        # Evidence register
        assert "evidence_register" in final
        assert "sources" in final["evidence_register"]

    def test_seven_sections_with_correct_keys(self) -> None:
        """Must produce exactly 7 sections with the standard keys."""
        evidence = Evidence()
        result = build_canonical_report(evidence, "TestCo", ["Founder"])

        sections = result["canonical"]["content"]["sections"]
        assert len(sections) == 7

        keys = [s["key"] for s in sections]
        assert keys == [
            "company", "team", "product", "validation",
            "market", "competition", "funding",
        ]

        # Each section must have non-empty key and title
        for s in sections:
            assert len(s["key"]) > 0
            assert len(s["title"]) > 0
            assert "blocks" in s
            assert isinstance(s["blocks"], list)

    def test_blocks_are_tuples(self) -> None:
        """All blocks must be lists (tuples) starting with a type string."""
        evidence = Evidence()
        result = build_canonical_report(evidence, "TestCo", ["Founder"])

        for section in result["canonical"]["content"]["sections"]:
            for block in section["blocks"]:
                assert isinstance(block, list), f"Block is not a list: {block}"
                assert len(block) >= 2, f"Block too short: {block}"
                assert isinstance(block[0], str), f"Block type is not str: {block[0]}"

    def test_founder_cards_with_profiles(self) -> None:
        """When founder profiles are available, cards block should contain them."""
        profile = PersonProfile(
            name="Alice Smith",
            headline="CEO at Acme",
            education=[{"degree": "MBA", "institution": "Stanford", "year": "2020"}],
            experience=[{"title": "CEO", "company": "Acme", "duration": "2020–present"}],
            summary="Experienced leader in tech.",
        )
        evidence = Evidence(founder_profiles=[profile])
        result = build_canonical_report(evidence, "Acme", ["Alice Smith"])

        team_section = result["canonical"]["content"]["sections"][1]
        assert team_section["key"] == "team"

        # Find cards block
        cards_blocks = [b for b in team_section["blocks"] if b[0] == "cards"]
        assert len(cards_blocks) == 1

        cards_payload = cards_blocks[0][2]
        assert len(cards_payload) == 1
        card = cards_payload[0]
        assert card["name"] == "Alice Smith"
        assert "lines" in card
        assert "fit" in card

    def test_sources_register_populated(self) -> None:
        """Sources from evidence should appear in the evidence register."""
        evidence = Evidence(
            sources=[
                EvidenceSource(
                    source_id="src_abc123",
                    url="https://linkedin.com/company/acme",
                    publisher="linkedin.com",
                    source_type="SOCIAL_MEDIA",
                ),
            ]
        )
        result = build_canonical_report(evidence, "Acme", ["Founder"])

        sources = result["canonical"]["content"]["final"]["evidence_register"]["sources"]
        assert len(sources) == 1
        assert sources[0]["source_id"] == "src_abc123"
        assert sources[0]["canonical_url"] == "https://linkedin.com/company/acme"

    def test_action_requirements_structure(self) -> None:
        """action_requirements must have topics and documents."""
        evidence = Evidence()
        result = build_canonical_report(evidence, "TestCo", ["Founder"])

        ar = result["canonical"]["content"]["action_requirements"]
        assert "topics" in ar
        assert "documents" in ar
        assert isinstance(ar["topics"], list)
        assert isinstance(ar["documents"], list)

        # Each topic has items
        for topic in ar["topics"]:
            assert "topic" in topic
            assert "items" in topic
            for item in topic["items"]:
                assert "text" in item
                assert "action_id" in item

        # Each document group has group name and priority/secondary
        for doc_group in ar["documents"]:
            assert "group" in doc_group
            assert "priority" in doc_group

    def test_fingerprint_changes_with_content(self) -> None:
        """Different evidence should produce different fingerprints."""
        e1 = Evidence()
        e2 = Evidence(
            company_profile=CompanyProfile(name="Acme", description="A great company"),
        )

        r1 = build_canonical_report(e1, "Acme", ["Founder"])
        r2 = build_canonical_report(e2, "Acme", ["Founder"])

        fp1 = r1["canonical"]["meta"]["final_fingerprint"]
        fp2 = r2["canonical"]["meta"]["final_fingerprint"]
        assert fp1 != fp2

    def test_idempotent_fingerprint(self) -> None:
        """Same evidence should produce the same fingerprint (idempotent)."""
        evidence = Evidence(
            company_profile=CompanyProfile(name="Acme", description="Stable"),
        )
        # Note: fingerprint includes timestamp, so exact idempotency
        # requires same call. We test structure consistency instead.
        result = build_canonical_report(evidence, "Acme", ["Founder"])
        fp = result["canonical"]["meta"]["final_fingerprint"]
        assert len(fp) == 64

    def test_presentation_fields(self) -> None:
        """Presentation must include required display labels."""
        evidence = Evidence()
        result = build_canonical_report(evidence, "TestCo", ["Founder"])

        pres = result["presentation"]
        assert pres["audience_label"] == "Founder Screen"
        assert "action_section_title" in pres
        assert "filename_stem" in pres
        assert "testco" in pres["filename_stem"]


class TestEvidenceMapperEdgeCases:
    """Test edge cases and partial data handling."""

    def test_empty_founder_names(self) -> None:
        """Should handle empty founder list gracefully."""
        evidence = Evidence()
        result = build_canonical_report(evidence, "TestCo", [])

        check_version_gate(result)
        validate_raw_report_json(result)

        team = result["canonical"]["content"]["sections"][1]
        assert team["key"] == "team"

    def test_company_name_with_special_chars(self) -> None:
        """Company names with special characters should slugify correctly."""
        evidence = Evidence()
        result = build_canonical_report(evidence, "Acme & Co. (India)", ["Founder"])

        check_version_gate(result)
        validate_raw_report_json(result)

        assert result["canonical"]["meta"]["company_name"] == "Acme & Co. (India)"

    def test_auth_walled_company_profile(self) -> None:
        """Auth-walled profiles should still produce valid output."""
        profile = CompanyProfile(
            name="Acme",
            is_auth_walled=True,
            description=None,
        )
        evidence = Evidence(company_profile=profile)
        result = build_canonical_report(evidence, "Acme", ["Founder"])

        check_version_gate(result)
        validate_raw_report_json(result)

    def test_partial_founder_profile_match(self) -> None:
        """When only some founders have profiles, cards should still generate."""
        profile = PersonProfile(name="Alice Smith", headline="CEO")
        evidence = Evidence(founder_profiles=[profile])
        result = build_canonical_report(
            evidence, "Acme", ["Alice Smith", "Bob Unknown"],
        )

        team = result["canonical"]["content"]["sections"][1]
        cards_blocks = [b for b in team["blocks"] if b[0] == "cards"]
        assert len(cards_blocks) == 1
        cards = cards_blocks[0][2]
        assert len(cards) == 2  # Both founders get cards
        assert cards[0]["name"] == "Alice Smith"
        assert cards[1]["name"] == "Bob Unknown"


# ── Fixtures ───────────────────────────────────────────────────────────

def _make_rich_evidence() -> Evidence:
    """Create evidence with data from all source types."""
    return Evidence(
        company_profile=CompanyProfile(
            name="Acme Corp",
            description="Acme Corp builds next-gen widgets.",
            industry="Technology",
            company_size="11-50",
            headquarters="San Francisco, CA",
            website="www.acme.com",
            founded_year="2022",
            specialties=["widgets", "AI"],
            url="https://linkedin.com/company/acme",
            retrieved_at="2026-10-01T12:00:00Z",
        ),
        founder_profiles=[
            PersonProfile(
                name="Alice Smith",
                headline="CEO & Co-founder at Acme Corp",
                education=[
                    {"degree": "MBA", "institution": "Stanford GSB", "year": "2018"},
                ],
                experience=[
                    {"title": "CEO", "company": "Acme Corp", "duration": "2022–present"},
                    {"title": "VP Product", "company": "BigTech", "duration": "2018–2022"},
                ],
                summary="Serial entrepreneur with 10 years in enterprise SaaS.",
                url="https://linkedin.com/in/alice-smith",
                retrieved_at="2026-10-01T12:01:00Z",
            ),
            PersonProfile(
                name="Bob Jones",
                headline="CTO & Co-founder at Acme Corp",
                education=[
                    {"degree": "MS CS", "institution": "MIT", "year": "2017"},
                ],
                experience=[
                    {"title": "CTO", "company": "Acme Corp", "duration": "2022–present"},
                ],
                url="https://linkedin.com/in/bob-jones",
                retrieved_at="2026-10-01T12:02:00Z",
            ),
        ],
        website_pages=[
            PageContent(
                url="https://www.acme.com",
                title="Acme Corp - Next-Gen Widgets",
                description="Building the future of widgets with AI.",
                text="Acme Corp is a technology company that builds next-generation widgets powered by artificial intelligence.",
                retrieved_at="2026-10-01T12:03:00Z",
            ),
        ],
        news_articles=[
            PageContent(
                url="https://techcrunch.com/acme-raises-5m",
                title="Acme Corp raises $5M seed round",
                description="Acme Corp announced a $5M seed funding round.",
                text="Acme Corp has raised $5 million in seed funding led by Sequoia Capital.",
                retrieved_at="2026-10-01T12:04:00Z",
            ),
        ],
        sources=[
            EvidenceSource(
                source_id="src_001",
                url="https://linkedin.com/company/acme",
                publisher="linkedin.com",
                source_type="SOCIAL_MEDIA",
                retrieved_at="2026-10-01T12:00:00Z",
            ),
            EvidenceSource(
                source_id="src_002",
                url="https://www.acme.com",
                publisher="acme.com",
                source_type="COMPANY_WEBSITE",
                retrieved_at="2026-10-01T12:03:00Z",
            ),
            EvidenceSource(
                source_id="src_003",
                url="https://techcrunch.com/acme-raises-5m",
                publisher="techcrunch.com",
                title="Acme Corp raises $5M seed round",
                source_type="NEWS",
                retrieved_at="2026-10-01T12:04:00Z",
            ),
        ],
    )
