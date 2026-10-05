"""Unit tests for audit snapshot sanitization, preservation of non-PII values, and idempotency."""
import json
import pytest
from app.domain.entities.discovery import (
    Evidence,
    PersonProfile,
    generate_content_fingerprint,
)
from app.application.mappers.evidence_to_report_mapper import build_canonical_report
from app.infrastructure.persistence.report_repo import sanitize_audit_snapshot


class TestAuditSnapshotSanitization:
    def test_sanitize_preserves_dates_amounts_ids_and_versions(self) -> None:
        """Verify that scrubbing email and phone PII does NOT alter dates, amounts, IDs, or version strings."""
        test_payload = {
            "dates": [
                "2023-03-15",
                "March 2023",
                "2019 - 2022",
                "2023-10-02T15:26:06Z",
            ],
            "amounts": [
                "$1.2M",
                "$10,000,000",
                "€500,000",
                "£2.5M",
                "1000+",
                "50M",
            ],
            "ids": [
                "0199a9a3-a006-79cf-916c-17e923e9c98a",
                "cs_mysa_202303",
                "NCT01234567",
            ],
            "versions": [
                "2.0.0",
                "1.4-beta",
                "vSET-Screening-v1",
                "commercial-screen-canonical.2",
            ],
            "company_name": "Mysa",
        }

        sanitized = sanitize_audit_snapshot(test_payload)

        # Dates must remain 100% untouched
        assert sanitized["dates"] == test_payload["dates"]

        # Amounts must remain 100% untouched
        assert sanitized["amounts"] == test_payload["amounts"]

        # IDs must remain 100% untouched
        assert sanitized["ids"] == test_payload["ids"]

        # Versions must remain 100% untouched
        assert sanitized["versions"] == test_payload["versions"]

    def test_sanitize_scrubs_emails_phones_and_photos(self) -> None:
        """Verify that emails, phone numbers, and photo URLs are stripped cleanly."""
        pii_payload = {
            "name": "Arpita Kapoor",
            "email": "arpita@mysa.io",
            "phone": "+91 9876543210",
            "mobile": "+1-555-0199",
            "avatar_url": "https://media.licdn.com/dms/image/v2/photo.jpg",
            "photo_url": "https://example.com/avatar.png",
            "raw_text": "Sensitive candidate transcript text",
            "pdf_base64": "JVBERi0xLjQK...",
            "notes": "Reach out to arpita@mysa.io or call +1 (555) 123-4567 regarding the $1.2M round on 2023-03-15.",
        }

        sanitized = sanitize_audit_snapshot(pii_payload)

        # Contact and photo keys must be deleted
        assert "email" not in sanitized
        assert "phone" not in sanitized
        assert "mobile" not in sanitized
        assert "avatar_url" not in sanitized
        assert "photo_url" not in sanitized
        assert "raw_text" not in sanitized
        assert "pdf_base64" not in sanitized

        # PII patterns in string fields must be scrubbed
        notes = sanitized["notes"]
        assert "arpita@mysa.io" not in notes
        assert "+1 (555) 123-4567" not in notes
        # But non-PII values inside the same string must be preserved
        assert "$1.2M" in notes
        assert "2023-03-15" in notes

    def test_final_fingerprint_computed_before_sanitization_for_idempotency(self) -> None:
        """Verify that final_fingerprint is computed before sanitization so report idempotency holds."""
        evidence = Evidence(
            founder_profiles=[
                PersonProfile(
                    name="Arpita Kapoor",
                    headline="CEO & Co-founder",
                    summary="Leading fintech platform. Contact: arpita@mysa.io",
                    experience=[{"company": "Mysa", "title": "CEO", "duration": "2023 - Present"}],
                    education=[{"school": "IIT Delhi", "degree": "B.Tech"}],
                )
            ]
        )
        report_data = build_canonical_report(evidence, company_name="Mysa", founder_names=["Arpita Kapoor"])

        meta = report_data["canonical"]["meta"]
        fp_before = meta["final_fingerprint"]
        assert fp_before.startswith("cs_") or len(fp_before) > 8

        # When the audit snapshot is sanitized and persisted:
        clean_snapshot = sanitize_audit_snapshot(report_data)

        # The snapshot retains the computed final_fingerprint and content_fingerprint
        assert clean_snapshot["canonical"]["meta"]["final_fingerprint"] == fp_before
        assert clean_snapshot["canonical"]["meta"]["canonical_content_fingerprint"] == meta["canonical_content_fingerprint"]

        # Fingerprint is deterministic and unchanged by sanitization of snapshots
        assert clean_snapshot["meta"]["canonical_content_fingerprint"] == fp_before

    def test_indian_and_unformatted_phone_numbers(self) -> None:
        """Verify scrubbing of Indian formatted, unformatted, and 0-prefixed phone numbers while keeping dates/amounts/IDs intact."""
        sample = {
            "entry_1": "Call on +91 98765 43210 for investor queries regarding $1.2M raised on 2023-03-15 (ID cs_mysa_202303).",
            "entry_2": "WhatsApp: 98765 43210. Valuation ₹50Cr as of 2023.",
            "entry_3": "Office landline/mobile: 09876543210. Report version 2.0.0, trial NCT01234567.",
            "entry_4": "Reach founder directly at 9876543210 (unformatted Indian mobile).",
            "entry_5": "Alternative desk line: +919876543210 with $500K committed.",
        }

        sanitized = sanitize_audit_snapshot(sample)

        # 1. Indian and unformatted phone numbers scrubbed
        assert "+91 98765 43210" not in sanitized["entry_1"]
        assert "98765 43210" not in sanitized["entry_2"]
        assert "09876543210" not in sanitized["entry_3"]
        assert "9876543210" not in sanitized["entry_4"]
        assert "+919876543210" not in sanitized["entry_5"]

        # 2. Dates, amounts, IDs, and versions must remain intact
        assert "$1.2M" in sanitized["entry_1"]
        assert "2023-03-15" in sanitized["entry_1"]
        assert "cs_mysa_202303" in sanitized["entry_1"]

        assert "₹50Cr" in sanitized["entry_2"]
        assert "2023" in sanitized["entry_2"]

        assert "2.0.0" in sanitized["entry_3"]
        assert "NCT01234567" in sanitized["entry_3"]

        assert "$500K" in sanitized["entry_5"]

