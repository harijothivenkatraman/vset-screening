from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient

from app.domain.entities.discovery import DiscoveryJob, JobState
from app.domain.entities.section import Section
from app.infrastructure.ingestion.import_service import merge_sections_preserve_quality, STATUS_RANK
from app.main import app
from app.config import get_settings


client = TestClient(app)


def test_merge_sections_never_downgrades_retrieved_founder_profile():
    report_id = uuid4()
    now = datetime.now(timezone.utc)

    # Existing section had verified retrieved profile with full experience
    old_founder_payload = {
        "founder_name": "Arpita Kapoor",
        "retrieval": {
            "status": "retrieved",
            "source_type": "linkedin_public",
        },
        "experience_timeline": [{"title": "Co-founder & CEO", "company": "Mysa"}],
        "education": [{"school": "IIIT"}],
    }
    existing_sections = [
        Section(
            id=uuid4(),
            report_id=report_id,
            key="team",
            title="Founder & team",
            position=0,
            ribbon=[["Tracked founders", "1"]],
            blocks=[["founder_profile", "Founder profile: Arpita Kapoor", old_founder_payload]],
            created_at=now,
        )
    ]

    # New incoming scrape was blocked by bot protection
    new_founder_payload = {
        "founder_name": "Arpita Kapoor",
        "retrieval": {
            "status": "blocked_by_bot_protection",
            "source_type": "linkedin_public",
        },
        "experience_timeline": [],
        "education": [],
    }
    incoming_sections = [
        Section(
            id=uuid4(),
            report_id=report_id,
            key="team",
            title="Founder & team",
            position=0,
            ribbon=[["Tracked founders", "1"]],
            blocks=[["founder_profile", "Founder profile: Arpita Kapoor", new_founder_payload]],
            created_at=now,
        )
    ]

    merged = merge_sections_preserve_quality(incoming_sections, existing_sections)
    assert len(merged) == 1
    team_sec = merged[0]
    block = team_sec.blocks[0]
    payload = block[2]

    # Quality preserved: status is still retrieved, not downgraded to blocked_by_bot_protection
    assert payload["retrieval"]["status"] == "retrieved"
    assert len(payload["experience_timeline"]) == 1
    assert payload["experience_timeline"][0]["title"] == "Co-founder & CEO"


def test_merge_sections_retains_old_blocks_if_new_is_empty():
    report_id = uuid4()
    now = datetime.now(timezone.utc)

    existing_sections = [
        Section(
            id=uuid4(),
            report_id=report_id,
            key="overview",
            title="Company Overview",
            position=0,
            ribbon=[],
            blocks=[["text", "Overview content", {"text": "Verified description"}]],
            created_at=now,
        )
    ]

    incoming_sections = [
        Section(
            id=uuid4(),
            report_id=report_id,
            key="overview",
            title="Company Overview",
            position=0,
            ribbon=[],
            blocks=[],  # Empty blocks from scrape failure
            created_at=now,
        )
    ]

    merged = merge_sections_preserve_quality(incoming_sections, existing_sections)
    assert len(merged) == 1
    assert len(merged[0].blocks) == 1
    assert merged[0].blocks[0][2]["text"] == "Verified description"


def test_status_rank_ordering():
    assert STATUS_RANK["retrieved"] > STATUS_RANK["identity_unverified"]
    assert STATUS_RANK["user_provided"] > STATUS_RANK["blocked_by_bot_protection"]
    assert STATUS_RANK["blocked_by_bot_protection"] > STATUS_RANK["not_found"]


def test_merge_sections_preserves_user_provided_founder_when_rerun_with_no_evidence():
    report_id = uuid4()
    now = datetime.now(timezone.utc)

    # Existing section has user_provided profile for Arpita Kapoor
    user_provided_payload = {
        "founder_name": "Arpita Kapoor",
        "retrieval": {
            "status": "user_provided",
            "source_type": "user_supplied",
            "retrieved_at": "2026-10-04T05:00:00Z",
        },
        "about": "Co-founder and CEO of Mysa with background in AI and robotics.",
        "experience_timeline": [{"title": "Co-founder & CEO", "company": "Mysa"}],
        "education": [{"school": "IIIT Hyderabad"}],
        "skills": ["Leadership", "Product Strategy"],
    }
    existing_sections = [
        Section(
            id=uuid4(),
            report_id=report_id,
            key="team",
            title="Founder & team",
            position=0,
            ribbon=[["Founding team", "1"]],
            blocks=[["founder_profile", "Founder profile: Arpita Kapoor", user_provided_payload]],
            created_at=now,
        )
    ]

    # Re-run with NO evidence -> scrape returned not_found / empty
    re_run_payload = {
        "founder_name": "Arpita Kapoor",
        "retrieval": {
            "status": "not_found",
            "source_type": "linkedin_public",
        },
        "experience_timeline": [],
        "education": [],
    }
    incoming_sections = [
        Section(
            id=uuid4(),
            report_id=report_id,
            key="team",
            title="Founder & team",
            position=0,
            ribbon=[["Founding team", "1"]],
            blocks=[["founder_profile", "Founder profile: Arpita Kapoor", re_run_payload]],
            created_at=now,
        )
    ]

    merged = merge_sections_preserve_quality(incoming_sections, existing_sections)
    assert len(merged) == 1
    team_sec = merged[0]
    block = team_sec.blocks[0]
    payload = block[2]

    # Quality preserved: status remains user_provided and rich fields remain intact
    assert payload["retrieval"]["status"] == "user_provided"
    assert payload["retrieval"]["source_type"] == "user_supplied"
    assert payload["about"] == "Co-founder and CEO of Mysa with background in AI and robotics."
    assert len(payload["experience_timeline"]) == 1
    assert payload["skills"] == ["Leadership", "Product Strategy"]


def test_merge_sections_preserves_user_provided_from_legacy_founder_profiles_section():
    report_id = uuid4()
    now = datetime.now(timezone.utc)

    # Legacy existing report had founder_profiles in a separate section
    user_provided_payload = {
        "founder_name": "Mohit Rangaraju",
        "retrieval": {
            "status": "user_provided",
            "source_type": "user_supplied",
            "retrieved_at": "2026-10-04T05:00:00Z",
        },
        "about": "Head of Engineering at Mysa.",
        "experience_timeline": [{"title": "Head of Engineering", "company": "Mysa"}],
        "education": [{"school": "BITS Pilani"}],
    }
    existing_sections = [
        Section(
            id=uuid4(),
            report_id=report_id,
            key="founder_profiles",
            title="Founder profiles",
            position=9,
            ribbon=[],
            blocks=[["founder_profile", "Founder profile: Mohit Rangaraju", user_provided_payload]],
            created_at=now,
        )
    ]

    # New incoming run only has team section (not founder_profiles)
    incoming_sections = [
        Section(
            id=uuid4(),
            report_id=report_id,
            key="team",
            title="Founder & team",
            position=1,
            ribbon=[["Founding team", "1"]],
            blocks=[[
                "founder_profile",
                "Founder profile: Mohit Rangaraju",
                {
                    "founder_name": "Mohit Rangaraju",
                    "retrieval": {"status": "blocked_by_bot_protection", "source_type": "linkedin_public"},
                    "experience_timeline": [],
                },
            ]],
            created_at=now,
        )
    ]

    merged = merge_sections_preserve_quality(incoming_sections, existing_sections)
    assert len(merged) == 1
    team_sec = merged[0]
    assert team_sec.key == "team"
    block = team_sec.blocks[0]
    payload = block[2]

    # Preserved user_provided from legacy founder_profiles into team
    assert payload["retrieval"]["status"] == "user_provided"
    assert payload["about"] == "Head of Engineering at Mysa."

