"""Unit tests for Founder Profiles tab, identity verification, privacy hardening, and cross-checks.

Covers:
1. Amendment 1: Identity verification (strong signal auto-attach, likely match on name+company, rejection of homonym/unrelated entities e.g. thermostat).
2. Amendment 2: Privacy (Contact block stripping, PII scrubbing, audit snapshot sanitization, DELETE cascade, and PII verification).
3. Amendment 3: LinkedIn Save to PDF parser fixture mirroring real layout (Contact, Top Skills, Languages, Certifications, Summary, Experience, Education) and web paste.
4. Amendment 4: Title normalization and cross-checks with false-positive resistance and low-severity "Differences found - verify" reporting.
"""
import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from app.application.services.founder_cross_check import FounderCrossCheckService
from app.application.services.identity_verifier import FounderIdentityVerifier
from app.application.services.pdf_extractor import (
    discard_contact_info,
    parse_manual_profile_text,
    sanitize_text,
)
from app.application.mappers.evidence_to_report_mapper import build_canonical_report
from app.domain.entities.discovery import (
    CrossCheckConflict,
    Evidence,
    EvidenceSource,
    ExperienceItem,
    PersonProfile,
    SourceDiagnostic,
)
from app.infrastructure.persistence.report_repo import sanitize_audit_snapshot
from app.config import get_settings
from app.main import app

VALID_API_KEY = get_settings().IMPORT_API_KEY


# ── Amendment 1: Identity Verification Tests ─────────────────────────────────

class TestFounderIdentityVerification:
    def test_strong_signal_website_near_name_auto_attaches(self) -> None:
        """URL found on company website near founder name must auto-attach."""
        profile = PersonProfile(name="Arpita Kapoor", headline="Co-founder at Mysa")
        res = FounderIdentityVerifier.verify(
            candidate_name="Arpita Kapoor",
            target_founder_name="Arpita Kapoor",
            company_name="Mysa",
            company_domain="mysa.io",
            candidate_profile=profile,
            url_source_type="website_near_name",
        )
        assert res.is_auto_attach is True
        assert res.identity_status == "verified"
        assert res.retrieval_status == "retrieved"

    def test_strong_signal_user_confirmed_auto_attaches(self) -> None:
        """URL confirmed by user in wizard / candidate review must auto-attach."""
        profile = PersonProfile(name="Mohit Rangaraju", headline="Co-founder & COO at Mysa")
        res = FounderIdentityVerifier.verify(
            candidate_name="Mohit Rangaraju",
            target_founder_name="Mohit Rangaraju",
            company_name="Mysa",
            company_domain="mysa.io",
            candidate_profile=profile,
            url_source_type="user_confirmed",
        )
        assert res.is_auto_attach is True
        assert res.identity_status == "verified"
        assert res.retrieval_status == "retrieved"

    def test_strong_signal_profile_links_domain_auto_attaches(self) -> None:
        """Profile that explicitly links company domain (mysa.io) in summary or experience must auto-attach."""
        profile = PersonProfile(
            name="Ashutosh Panigrahi",
            headline="Co-founder & CTO",
            summary="Building financial infrastructure at https://mysa.io for growing businesses.",
        )
        res = FounderIdentityVerifier.verify(
            candidate_name="Ashutosh Panigrahi",
            target_founder_name="Ashutosh Panigrahi",
            company_name="Mysa",
            company_domain="mysa.io",
            candidate_profile=profile,
            url_source_type="search_discovery",
        )
        assert res.is_auto_attach is True
        assert res.identity_status == "verified"
        assert res.retrieval_status == "retrieved"
        assert "mysa.io" in res.reason

    def test_name_and_company_mention_alone_requires_confirmation(self) -> None:
        """Name + company mention alone without domain verification must NOT auto-attach."""
        profile = PersonProfile(
            name="Arpita Kapoor",
            headline="Co-founder at Mysa",
            summary="Fintech executive based in Bengaluru.",
        )
        res = FounderIdentityVerifier.verify(
            candidate_name="Arpita Kapoor",
            target_founder_name="Arpita Kapoor",
            company_name="Mysa",
            company_domain="mysa.io",
            candidate_profile=profile,
            url_source_type="search_discovery",
        )
        assert res.is_auto_attach is False
        assert res.identity_status == "likely_match"
        assert res.retrieval_status == "identity_unverified"
        assert "Requires user verification" in res.reason

    def test_same_name_unrelated_company_rejected(self) -> None:
        """Profile at an unrelated company that merely contains 'Mysa' (e.g. thermostat) must NOT be auto-attached."""
        profile = PersonProfile(
            name="Arpita Kapoor",
            headline="Hardware Engineer at Mysa Smart Thermostats",
            summary="Working on smart home climate control and HVAC heating thermostats.",
            experience=[{"title": "Hardware Engineer", "company": "Mysa Smart Thermostats"}],
        )
        res = FounderIdentityVerifier.verify(
            candidate_name="Arpita Kapoor",
            target_founder_name="Arpita Kapoor",
            company_name="Mysa",
            company_domain="mysa.io",
            candidate_profile=profile,
            url_source_type="search_discovery",
        )
        assert res.is_auto_attach is False
        assert res.retrieval_status == "not_found"
        assert "unrelated entity" in res.reason.lower()

    def test_name_mismatch_rejected(self) -> None:
        """Candidate with different name is rejected immediately."""
        profile = PersonProfile(name="David Smith", headline="CEO at Mysa")
        res = FounderIdentityVerifier.verify(
            candidate_name="David Smith",
            target_founder_name="Arpita Kapoor",
            company_name="Mysa",
            company_domain="mysa.io",
            candidate_profile=profile,
        )
        assert res.is_auto_attach is False
        assert res.retrieval_status == "not_found"
        assert "Name mismatch" in res.reason


# ── Amendment 4: Title Normalization & Cross-Check Tests ──────────────────────

class TestFounderCrossCheck:
    def test_title_normalization_ceo_co_founder(self) -> None:
        """'CEO & Co-founder' on website vs 'Chief Executive Officer, Co-Founder' on LinkedIn must NOT conflict."""
        experiences = [
            ExperienceItem(
                title="Chief Executive Officer, Co-Founder",
                company="Mysa",
                start="March 2023",
                end="Present",
                is_current=True,
            )
        ]
        conflicts = FounderCrossCheckService.cross_check_founder_role(
            founder_name="Arpita Kapoor",
            website_role="CEO & Co-founder",
            experiences=experiences,
            company_name="Mysa",
        )
        assert len(conflicts) == 0

    def test_title_normalization_cto_and_founder(self) -> None:
        """'Chief Technology Officer & Co-founder' vs 'CTO and Founder' must NOT conflict."""
        experiences = [
            ExperienceItem(
                title="CTO and Founder",
                company="Mysa",
                start="2023",
                end="Present",
                is_current=True,
            )
        ]
        conflicts = FounderCrossCheckService.cross_check_founder_role(
            founder_name="Ashutosh Panigrahi",
            website_role="Chief Technology Officer & Co-founder",
            experiences=experiences,
            company_name="Mysa",
        )
        assert len(conflicts) == 0

    def test_genuine_title_discrepancy_reported(self) -> None:
        """Website states 'CEO', but LinkedIn current position is 'Chief Technology Officer'."""
        experiences = [
            ExperienceItem(
                title="Chief Technology Officer",
                company="Mysa",
                start="2023",
                end="Present",
                is_current=True,
            )
        ]
        conflicts = FounderCrossCheckService.cross_check_founder_role(
            founder_name="Arpita Kapoor",
            website_role="Chief Executive Officer",
            experiences=experiences,
            company_name="Mysa",
        )
        assert len(conflicts) == 1
        conf = conflicts[0]
        assert conf.severity == "low"
        assert "Differences found - verify" in conf.details
        assert "Chief Executive Officer" in conf.details
        assert "Chief Technology Officer" in conf.details

    def test_position_not_at_company_ignored(self) -> None:
        """If LinkedIn current position is at an unrelated company, rule specifies DO NOT compare."""
        experiences = [
            ExperienceItem(
                title="Senior Director",
                company="OtherCorp",
                start="2024",
                end="Present",
                is_current=True,
            )
        ]
        conflicts = FounderCrossCheckService.cross_check_founder_role(
            founder_name="Mohit Rangaraju",
            website_role="Co-founder & COO",
            experiences=experiences,
            company_name="Mysa",
        )
        assert len(conflicts) == 0


# ── Amendment 3: Real LinkedIn "Save to PDF" Parser Fixture Tests ─────────────

class TestLinkedInPdfParserLayout:
    def test_real_linkedin_save_to_pdf_layout(self) -> None:
        """Mirrors real LinkedIn 'Save to PDF' export with Contact, Top Skills, Languages, Certifications, Summary, Experience, Education."""
        fixture_pdf_text = """
        Contact
        www.linkedin.com/in/arpita-kapoor-123 (LinkedIn)
        arpita.kapoor@example.com (Email)
        +91 9876543210 (Mobile)

        Top Skills
        Financial Modeling
        Product Strategy
        Fintech

        Languages
        English (Full Professional)
        Hindi (Native or Bilingual)

        Certifications
        Chartered Financial Analyst (CFA)

        Summary
        Co-Founder & CEO at Mysa. Building the next generation financial operating platform for modern enterprises.

        Experience
        Mysa
        Chief Executive Officer
        March 2023 - Present (3 years 1 month)
        Bengaluru, Karnataka, India
        Leading company strategy and product roadmap.

        Razorpay
        Vice President of Product
        January 2019 - February 2023 (4 years 2 months)
        Bengaluru, India

        Education
        Indian Institute of Technology, Delhi
        Bachelor of Technology - BTech, Computer Science
        2011 - 2015
        """

        parsed = parse_manual_profile_text(fixture_pdf_text)

        # 1. Contact block must be discarded
        assert "arpita.kapoor@example.com" not in str(parsed)
        assert "+91 9876543210" not in str(parsed)
        assert "arpita-kapoor-123" not in str(parsed)

        # 2. Skills and Certifications
        assert "Financial Modeling" in parsed["skills"]
        assert "Fintech" in parsed["skills"]
        assert "Chartered Financial Analyst (CFA)" in parsed["certifications"]
        assert "English (Full Professional)" in parsed["languages"]

        # 3. Summary
        assert "Co-Founder & CEO at Mysa" in parsed["summary"]

        # 4. Experience timeline (Company -> Title -> Dates)
        assert len(parsed["experience"]) >= 2
        exp0 = parsed["experience"][0]
        assert exp0["company"] == "Mysa"
        assert exp0["title"] == "Chief Executive Officer"
        assert exp0["start"] == "March 2023"
        assert exp0["end"] == "Present"
        assert exp0["is_current"] is True
        assert "3 years 1 month" in exp0["duration"]

        exp1 = parsed["experience"][1]
        assert exp1["company"] == "Razorpay"
        assert "Vice President" in exp1["title"]
        assert exp1["is_current"] is False

        # 5. Education
        assert len(parsed["education"]) >= 1
        edu0 = parsed["education"][0]
        assert "IIT" in edu0["school"] or "Indian Institute of Technology" in edu0["school"]
        assert "BTech" in edu0["degree"]
        assert edu0["start_year"] == "2011"
        assert edu0["end_year"] == "2015"

    def test_missing_dates_and_present_handled(self) -> None:
        """Handles missing date ranges gracefully and detects 'Present' without crashing."""
        sample_text = """
        Experience
        Mysa
        Co-founder
        Present

        Previous Startup
        Advisor
        """
        parsed = parse_manual_profile_text(sample_text)
        assert len(parsed["experience"]) >= 2
        assert parsed["experience"][0]["is_current"] is True


# ── Amendment 2: Privacy, Snapshot Sanitization & Cascade Deletion ───────────

class TestPrivacyAndCascadeDeletion:
    def test_sanitize_audit_snapshot_scrubs_pii_and_photos(self) -> None:
        """Audit snapshots must not contain raw profile text, contact info or photo URLs."""
        raw_snapshot = {
            "meta": {"company_name": "Mysa"},
            "profile": {
                "name": "Arpita Kapoor",
                "email": "arpita@mysa.io",
                "phone": "+91 9876543210",
                "avatar_url": "https://media.licdn.com/dms/image/v2/C5603AQ/profile.jpg",
                "photo_url": "https://example.com/photo.png",
                "raw_text": "Pasted CV text with confidential notes",
                "pdf_base64": "JVBERi0xLjQK...",
                "headline": "CEO at Mysa",
                "bio": "Reach me at secret@domain.com or +1-555-0199 for inquiries.",
            },
        }

        clean = sanitize_audit_snapshot(raw_snapshot)

        # Contact keys stripped
        assert "email" not in clean["profile"]
        assert "phone" not in clean["profile"]
        assert "avatar_url" not in clean["profile"]
        assert "photo_url" not in clean["profile"]
        assert "raw_text" not in clean["profile"]
        assert "pdf_base64" not in clean["profile"]

        # String values scrubbed of emails and phone numbers
        bio = clean["profile"]["bio"]
        assert "secret@domain.com" not in bio
        assert "+1-555-0199" not in bio
        assert "Reach me at" in bio

    @pytest.mark.asyncio
    async def test_delete_company_cascade_and_pii_absence(self, client: AsyncClient) -> None:
        """Test full company deletion cascade and verify PII does not leak into DB or API."""
        company_slug = f"privacy-test-{uuid.uuid4().hex[:6]}"

        # 1. Import a test report with manual evidence containing contact info
        evidence = Evidence(
            founder_profiles=[
                PersonProfile(
                    name="Test Founder",
                    headline="CEO & Founder",
                    summary="Building test infrastructure.",
                    experience=[{"company": "PrivacyCo", "title": "CEO", "duration": "2023 - Present"}],
                    education=[{"school": "Test University", "degree": "B.S."}],
                )
            ]
        )
        report_dict = build_canonical_report(evidence, company_name=company_slug, founder_names=["Test Founder"])

        import_resp = await client.post(
            "/api/v1/reports/import",
            json=report_dict,
            headers={"X-API-Key": VALID_API_KEY},
        )
        assert import_resp.status_code == 200

        # 2. Verify team section is present in report navigation
        nav_resp = await client.get(f"/api/v1/companies/{company_slug}/sections")
        assert nav_resp.status_code == 200
        section_keys = [s["key"] for s in nav_resp.json()["sections"]]
        assert "team" in section_keys

        # 3. Verify section content contains founder profile block and NO contact info
        sec_resp = await client.get(f"/api/v1/companies/{company_slug}/sections/team")
        assert sec_resp.status_code == 200
        sec_json = sec_resp.json()
        assert "@" not in str(sec_json)
        assert any(b[0] == "founder_profile" for b in sec_json["blocks"])

        # 4. Verify DELETE /api/v1/companies/{slug} requires API key
        unauth_del = await client.delete(f"/api/v1/companies/{company_slug}?confirm={company_slug}")
        assert unauth_del.status_code in (401, 403)

        # 4b. Verify DELETE without matching ?confirm=<slug> fails with 400 Bad Request
        mismatch_del = await client.delete(
            f"/api/v1/companies/{company_slug}?confirm=wrong-slug",
            headers={"X-API-Key": VALID_API_KEY},
        )
        assert mismatch_del.status_code == 400

        # 5. Execute authorized DELETE /api/v1/companies/{slug}?confirm=<slug>
        del_resp = await client.delete(
            f"/api/v1/companies/{company_slug}?confirm={company_slug}",
            headers={"X-API-Key": VALID_API_KEY},
        )
        assert del_resp.status_code == 200
        assert del_resp.json()["deleted"] is True

        # 6. Verify cascade: company and all child sections return 404
        get_comp = await client.get(f"/api/v1/companies/{company_slug}")
        assert get_comp.status_code == 404

        get_sec = await client.get(f"/api/v1/companies/{company_slug}/sections/team")
        assert get_sec.status_code == 404
