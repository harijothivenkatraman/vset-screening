"""Script to seed demo companies with clearly fictional personas for local UI testing.

CRITICAL: Never use real people or company names in demo fixtures.
"""
import asyncio
from datetime import datetime, timezone
import json

from app.application.mappers.evidence_to_report_mapper import build_canonical_report
from app.infrastructure.ingestion.import_service import ReportImportService
from app.domain.entities.discovery import (
    Evidence,
    EvidenceSource,
    PageContent,
    PersonProfile,
    SourceDiagnostic,
)
from app.config import get_settings
from app.infrastructure.persistence.database import async_session_factory


import os


async def seed() -> None:
    env = os.environ.get("ENVIRONMENT", "").lower()
    if env == "production" or get_settings().ENVIRONMENT.lower() == "production":
        raise RuntimeError("CRITICAL SAFETY GUARD: Demo seed scripts must never execute in production (ENVIRONMENT=production). Seeding aborted.")


    async with async_session_factory() as session:
        import_service = ReportImportService(session)

        # ── 1. Demo Retrieved: Fictional retrieved profile ──
        ev_retrieved = Evidence(
            founder_profiles=[
                PersonProfile(
                    name="Jane Example",
                    headline="CEO & Founder at ExampleCorp",
                    location="Metropolis, Country",
                    summary="Founder & CEO of ExampleCorp. Fictional test persona for component validation.",
                    url="https://www.linkedin.com/in/jane-example-fictional",
                    retrieved_at="2026-10-01T12:00:00Z",
                    experience=[
                        {"title": "Chief Executive Officer", "company": "ExampleCorp", "duration": "2023 - Present", "is_current": True, "description": "General corporate oversight."},
                        {"title": "Senior Engineer", "company": "Fictional Tech Labs", "duration": "2018 - 2023", "is_current": False, "description": "Software architecture."},
                    ],
                    education=[
                        {"school": "Metropolis University", "degree": "B.S. Computer Science", "start_year": "2014", "end_year": "2018"},
                    ],
                    skills=["Software Engineering", "Systems Architecture"],
                    certifications=["Example Certified Professional · 2022"],
                    languages=["English"],
                ),
            ],
            sources=[
                EvidenceSource(source_id="src_jane", url="https://www.linkedin.com/in/jane-example-fictional", publisher="LinkedIn", source_type="SOCIAL_MEDIA", title="Jane Example - LinkedIn", retrieved_at="2026-10-01T12:00:00Z"),
            ],
        )
        rep1 = build_canonical_report(ev_retrieved, "demo-fictional-retrieved", ["Jane Example"])
        rep1["canonical"]["meta"]["company_name"] = "ExampleCorp (Retrieved Profile Demo)"
        await import_service.import_report(rep1)

        # ── 2. Demo User-Provided: Fictional user-supplied profile ──
        ev_manual = Evidence(
            founder_profiles=[
                PersonProfile(
                    name="Alex Testperson",
                    headline="CTO & Co-Founder at TestVentures",
                    location="Gotham City, Country",
                    summary="Fictional test executive provided by user.",
                    url="manual:founder_alex_testperson",
                    retrieved_at="2026-10-01T12:00:00Z",
                    experience=[
                        {"title": "Chief Technology Officer", "company": "TestVentures", "duration": "2023 - Present", "is_current": True},
                    ],
                    education=[
                        {"school": "Gotham Institute of Technology", "degree": "B.Eng", "start_year": "2015", "end_year": "2019"},
                    ],
                    skills=["Cloud Systems", "Database Design"],
                ),
            ],
            sources=[
                EvidenceSource(source_id="src_manual_alex", url="manual:founder_alex_testperson", publisher="User upload (unverified)", source_type="USER_SUPPLIED", title="User-Provided Profile - Alex Testperson", retrieved_at="2026-10-01T12:00:00Z"),
            ],
        )
        rep2 = build_canonical_report(ev_manual, "demo-fictional-user-provided", ["Alex Testperson"])
        rep2["canonical"]["meta"]["company_name"] = "TestVentures (User-Provided Evidence Demo)"
        await import_service.import_report(rep2)

        # ── 3. Demo Blocked: Fictional blocked state ──
        ev_blocked = Evidence(
            diagnostics=[
                SourceDiagnostic(url="https://www.linkedin.com/in/bob-sample-fictional", outcome="blocked_by_bot_protection", bytes_fetched=1024),
            ],
            founder_profiles=[
                PersonProfile(name="Bob Sample", url="https://www.linkedin.com/in/bob-sample-fictional"),
            ]
        )
        rep3 = build_canonical_report(ev_blocked, "demo-fictional-blocked", ["Bob Sample"])
        rep3["canonical"]["meta"]["company_name"] = "SampleCorp (Blocked Scraper State Demo)"
        await import_service.import_report(rep3)

        # ── 4. Demo Unverified: Likely Match requiring user confirmation ──
        p_unverified = PersonProfile(
            name="Charlie Candidate",
            headline="VP Operations at Unrelated Company Inc",
            location="Springfield, Country",
            summary="Fictional profile from an unrelated business entity.",
            url="https://www.linkedin.com/in/charlie-candidate-unrelated",
            retrieved_at="2026-10-01T12:00:00Z",
            identity_status="likely_match",
            verification_reason="Candidate matches name but works at an unrelated business entity.",
            experience=[
                {"title": "VP Operations", "company": "Unrelated Company Inc", "duration": "2021 - Present", "is_current": True},
            ],
        )
        ev_unverified = Evidence(
            founder_profiles=[p_unverified],
            website_pages=[
                PageContent(
                    url="https://fictional-company.test/team",
                    title="Team - Fictional Company",
                    description="Leadership",
                    text="Charlie Candidate - Co-founder & CEO",
                )
            ],
            sources=[
                EvidenceSource(source_id="src_charlie_unverified", url="https://www.linkedin.com/in/charlie-candidate-unrelated", publisher="LinkedIn", source_type="SOCIAL_MEDIA", title="Candidate Profile (Unverified)", retrieved_at="2026-10-01T12:00:00Z"),
            ],
        )
        rep4 = build_canonical_report(ev_unverified, "demo-fictional-unverified", ["Charlie Candidate"])
        rep4["canonical"]["meta"]["company_name"] = "Fictional Co (Identity Unverified Candidate Demo)"
        await import_service.import_report(rep4)

        await session.commit()
        print("Successfully seeded all 4 fictional demo screening reports!")

if __name__ == "__main__":
    asyncio.run(seed())
