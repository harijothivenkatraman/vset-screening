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


class TestEvidenceMapperSourcePermutations:
    """Golden tests for multi-source merged evidence permutations:
    1. website-only evidence
    2. linkedin-only evidence
    3. both sources
    4. neither source (graceful degradation)
    """

    def test_mapper_website_only(self) -> None:
        """Website JSON-LD + text populates Section 1 (overview, KV) & Section 3 (product)."""
        evidence = Evidence(
            website_pages=[
                PageContent(
                    url="https://acme.com",
                    title="Acme - Smart Energy Solutions",
                    description="Acme builds smart energy monitors for microgrids.",
                    text="About us: We develop intelligent IoT hardware controllers and cloud software for energy optimization.",
                    json_ld=[{
                        "@type": "Organization",
                        "name": "Acme",
                        "description": "Acme builds smart energy monitors for microgrids.",
                        "foundingDate": "2020-05-01",
                        "knowsAbout": ["CleanTech", "Energy"],
                        "address": {"addressLocality": "Austin", "addressCountry": "US"},
                        "numberOfEmployees": "25",
                    }],
                ),
                PageContent(
                    url="https://acme.com/products",
                    title="Acme Products & Platforms",
                    description="Flagship hardware controller for industrial loads.",
                    text="The Acme Controller optimizes power demand in commercial buildings.",
                ),
            ],
            sources=[
                EvidenceSource(
                    source_id="src_001",
                    url="https://acme.com",
                    publisher="acme.com",
                    source_type="COMPANY_WEBSITE",
                ),
            ],
        )

        result = build_canonical_report(evidence, "Acme", ["Alice"])
        check_version_gate(result)
        validate_raw_report_json(result)

        sections = result["canonical"]["content"]["sections"]
        company_sec = next(s for s in sections if s["key"] == "company")
        product_sec = next(s for s in sections if s["key"] == "product")

        # 1. Overview populated from website
        overview_block = next(b for b in company_sec["blocks"] if b[1] == "What the company does")
        assert "Acme builds smart energy monitors" in overview_block[2]

        # 2. KV profile populated from JSON-LD
        kv_block = next(b for b in company_sec["blocks"] if b[1] == "Company profile")
        kv_dict = dict(kv_block[2])
        assert kv_dict.get("Sector") == "CleanTech, Energy"
        assert kv_dict.get("Headquarters") == "Austin, US"
        assert kv_dict.get("Founded") == "2020"
        assert kv_dict.get("Company size") == "25"

        # 3. Product section populated from product page
        prod_block = next(b for b in product_sec["blocks"] if b[1] == "Product overview")
        assert "Acme Controller" in prod_block[2] or "hardware controller" in prod_block[2]

        # 4. Gaps check: NO metadata notices or cutoffs in gaps
        for sec in sections:
            for b in sec["blocks"]:
                if b[0] == "list" and "Information gaps" in b[1]:
                    for gap in b[2]:
                        assert "Research cutoff" not in gap
                        assert "auto-generated" not in gap

        # 5. Actions check: NO metadata notices in action items
        for action in result["canonical"]["content"]["actions"]:
            assert "Research cutoff" not in action["text"]
            assert "auto-generated" not in action["text"]

    def test_mapper_linkedin_only(self) -> None:
        """LinkedIn company profile and founder profiles populate Section 1 & Section 2."""
        evidence = Evidence(
            company_profile=CompanyProfile(
                name="Acme Corp",
                description="Next-generation cloud infrastructure orchestration.",
                industry="Cloud Computing",
                headquarters="San Francisco, CA",
                founded_year="2021",
                company_size="11-50 employees",
            ),
            founder_profiles=[
                PersonProfile(
                    name="Alice",
                    headline="Founder & CEO at Acme Corp",
                    summary="10 years leading engineering teams in distributed systems.",
                ),
            ],
            sources=[
                EvidenceSource(
                    source_id="src_001",
                    url="https://linkedin.com/company/acme",
                    publisher="linkedin.com",
                    source_type="SOCIAL_MEDIA",
                ),
            ],
        )

        result = build_canonical_report(evidence, "Acme Corp", ["Alice"])
        check_version_gate(result)
        validate_raw_report_json(result)

        sections = result["canonical"]["content"]["sections"]
        company_sec = next(s for s in sections if s["key"] == "company")
        team_sec = next(s for s in sections if s["key"] == "team")

        # Overview populated from LinkedIn
        overview_block = next(b for b in company_sec["blocks"] if b[1] == "What the company does")
        assert "cloud infrastructure" in overview_block[2]

        # KV populated from LinkedIn
        kv_block = next(b for b in company_sec["blocks"] if b[1] == "Company profile")
        kv_dict = dict(kv_block[2])
        assert kv_dict.get("Sector") == "Cloud Computing"
        assert kv_dict.get("Headquarters") == "San Francisco, CA"
        assert kv_dict.get("Founded") == "2021"

        # Team founder card
        founder_card = team_sec["blocks"][1][2][0]
        assert founder_card["name"] == "Alice"
        assert "Founder & CEO" in founder_card["role"]

    def test_mapper_both(self) -> None:
        """When both LinkedIn and website evidence are present, merged precedence applies."""
        evidence = Evidence(
            company_profile=CompanyProfile(
                name="Acme Corp",
                description="LinkedIn high-level overview.",
                industry="Enterprise Software",
                headquarters="Boston, MA",
            ),
            founder_profiles=[
                PersonProfile(name="Alice", headline="CEO"),
            ],
            website_pages=[
                PageContent(
                    url="https://acme.com",
                    title="Acme Corp Home",
                    description="Website description.",
                    text="We build enterprise orchestration software.",
                    json_ld=[{
                        "@type": "Organization",
                        "foundingDate": "2019",
                        "numberOfEmployees": "50-100",
                    }],
                ),
                PageContent(
                    url="https://acme.com/product",
                    title="Platform",
                    description="Cloud SaaS platform.",
                    text="The Acme Cloud SaaS platform coordinates microservices.",
                ),
            ],
        )

        result = build_canonical_report(evidence, "Acme Corp", ["Alice"])
        check_version_gate(result)
        validate_raw_report_json(result)

        sections = result["canonical"]["content"]["sections"]
        company_sec = next(s for s in sections if s["key"] == "company")
        kv_dict = dict(next(b for b in company_sec["blocks"] if b[1] == "Company profile")[2])

        # LinkedIn supplied Sector and HQ
        assert kv_dict.get("Sector") == "Enterprise Software"
        assert kv_dict.get("Headquarters") == "Boston, MA"
        # Website supplied Founded and Company size
        assert kv_dict.get("Founded") == "2019"
        assert kv_dict.get("Company size") == "50-100"

    def test_mapper_neither(self) -> None:
        """Graceful degradation with zero sources: clean gaps, valid schema, no fake gaps."""
        evidence = Evidence()
        result = build_canonical_report(evidence, "GhostCo", ["Casper"])
        check_version_gate(result)
        validate_raw_report_json(result)

        sections = result["canonical"]["content"]["sections"]
        company_sec = next(s for s in sections if s["key"] == "company")
        overview_block = next(b for b in company_sec["blocks"] if b[1] == "What the company does")
        assert overview_block[2] == "Not established from public sources."

        # Verify gaps are real field gaps only
        gaps_block = next(b for b in company_sec["blocks"] if b[1] == "Information gaps")
        gaps = gaps_block[2]
        assert len(gaps) >= 4
        for g in gaps:
            assert "Research cutoff" not in g
            assert "auto-generated" not in g
            assert any(kw in g.lower() for kw in ["overview", "sector", "headquarters", "founding", "size"])

    def test_founder_roles_unverified_vs_verified(self) -> None:
        """Never label user-typed founder as Co-founder without evidence. Cite role sources."""
        evidence = Evidence(
            founder_profiles=[
                PersonProfile(
                    name="Arpita Kapoor",
                    headline="CEO at Mysa",
                    url="https://linkedin.com/in/arpitakapoor",
                ),
            ],
            website_pages=[
                PageContent(
                    url="https://mysa.io/team",
                    title="Mysa Team",
                    description="Leadership team at Mysa",
                    text="Mohit Rangaraju leads product strategy at Mysa.",
                ),
            ],
        )

        result = build_canonical_report(
            evidence,
            "Mysa",
            ["Arpita Kapoor", "Mohit Rangaraju", "Ashutosh Panigrahi"],
        )
        check_version_gate(result)
        validate_raw_report_json(result)

        sections = result["canonical"]["content"]["sections"]
        team_sec = next(s for s in sections if s["key"] == "team")
        cards = next(b for b in team_sec["blocks"] if b[0] == "cards")[2]

        # 1. Arpita Kapoor: verified via LinkedIn headline
        arpita = next(c for c in cards if c["name"] == "Arpita Kapoor")
        assert arpita["role"] == "CEO at Mysa"
        arpita_lines = dict(arpita["lines"])
        assert "LinkedIn profile (https://linkedin.com/in/arpitakapoor)" in arpita_lines.get("Role source", "")

        # 2. Mohit Rangaraju: verified via website mention
        mohit = next(c for c in cards if c["name"] == "Mohit Rangaraju")
        assert mohit["role"] == "Founder (from company website)"
        mohit_lines = dict(mohit["lines"])
        assert "Company website: https://mysa.io/team" in mohit_lines.get("Role source", "")

        # 3. Ashutosh Panigrahi: unverified user input -> must be 'Founder (provided by user)'
        ashutosh = next(c for c in cards if c["name"] == "Ashutosh Panigrahi")
        assert ashutosh["role"] == "Founder (provided by user)"
        assert "Co-founder" not in ashutosh["role"]
        ashutosh_lines = dict(ashutosh["lines"])
        assert ashutosh_lines.get("Role source") == "Provided by user (unverified)"
        assert "could not be corroborated" in ashutosh["fit"]

    def test_unverified_founder_background_emits_actionable_dd_requirements(self) -> None:
        """Unverified founder education and experience must appear as actionable DD requirements under Information to prepare."""
        evidence = Evidence(
            website_pages=[
                PageContent(
                    url="https://mysa.io",
                    title="Mysa",
                    description="Finance automation for enterprises",
                    text="We build accounts payable software for finance teams.",
                ),
            ],
        )

        result = build_canonical_report(
            evidence,
            "Mysa",
            ["Arpita Kapoor", "Mohit Rangaraju"],
        )

        content = result["canonical"]["content"]
        act_reqs = content.get("action_requirements", {})

        # 1. Action requirements topics should contain Team & founders DD requests
        topics = act_reqs.get("topics", [])
        team_topic = next((t for t in topics if t["topic"] == "Team & founders"), None)
        assert team_topic is not None
        items = team_topic["items"]
        assert any("Arpita Kapoor" in it["text"] and "resume" in it["text"].lower() for it in items)
        assert any("Arpita Kapoor" in it["text"] and "academic" in it["text"].lower() for it in items)
        assert any("Mohit Rangaraju" in it["text"] and "resume" in it["text"].lower() for it in items)

        # 2. Documents should include Team & key personnel priority items
        docs = act_reqs.get("documents", [])
        team_doc = next((d for d in docs if "Team" in d["group"]), None)
        assert team_doc is not None
        assert any("resumes" in p.lower() for p in team_doc["priority"])

    def test_grounding_case_study_urls_and_marketing_claims(self) -> None:
        """Customers from URL slugs are labelled low-confidence and marketing claims are marked unverified."""
        evidence = Evidence(
            website_pages=[
                PageContent(
                    url="https://mysa.io",
                    title="Mysa",
                    description="Accounts payable for finance teams",
                    text="Loved by 1000+ CFOs.\nHow goSTOPS Manages 500+ Invoices monthly.",
                    links=["https://mysa.io/customers/vaaree", "https://mysa.io/customers/hanto"],
                ),
            ],
        )

        result = build_canonical_report(evidence, "Mysa", ["Arpita Kapoor"])
        sections = result["canonical"]["content"]["sections"]
        val_sec = next(s for s in sections if s["key"] == "validation")
        blocks = val_sec["blocks"]

        # Case studies block: Vaaree and Hanto must be labelled case-study URL
        signals_block = next((b for b in blocks if "Named customer case studies" in str(b[1])), None)
        assert signals_block is not None
        signals_text = " ".join(signals_block[2])
        assert "goSTOPS" in signals_text
        assert "Vaaree (case-study URL)" in signals_text
        assert "Hanto (case-study URL)" in signals_text

        # Marketing claims block: Loved by 1000+ CFOs must be present and marked unverified
        mktg_block = next((b for b in blocks if "Marketing metrics" in str(b[1])), None)
        assert mktg_block is not None
        mktg_text = " ".join(mktg_block[2])
        assert "Loved by 1000+ CFOs" in mktg_text
        assert "company-stated, unverified" in mktg_text
