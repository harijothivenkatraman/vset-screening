#!/usr/bin/env python3
"""Migration script to seed Founder Profiles ONLY from canonical reference/*.json screens.

Complies strictly with Phase 0 / Phase 1 requirements (Amendment 1):
1. Import ONLY from reference/*.json (e.g. Mysa, TerraSpark).
2. Set source label: "From vSET reference screen, <date>".
3. Skip every auto-discovered company (discovery-*, dimdot, etc.).
4. Run in --dry-run by default; do not write unless explicitly requested with --execute.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path
import re
import sys
from typing import Any
from uuid import uuid4

# Ensure backend directory is in sys.path
root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.application.use_cases.add_from_evidence import generate_founder_slug
from app.domain.entities.founder_profile import (
    EducationItem,
    ExperienceTimelineItem,
    FounderProfile,
    RetrievalPayload,
)
from app.infrastructure.persistence.database import async_session_factory, init_db
from app.infrastructure.persistence.sqlite_founder_repository import (
    SqliteFounderProfileRepository,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("migrate_from_dashboard")


def clean_text(s: str) -> str:
    """Normalize Unicode replacement characters, hyphens, and whitespace."""
    s = (
        s.replace("\x96", " - ")
        .replace("\x97", " - ")
        .replace("\ufffd", " - ")
        .replace("\u2013", "-")
        .replace("\u2014", " - ")
        .replace("\xb7", " - ")
        .replace("·", " - ")
        .replace("•", " - ")
    )
    s = re.sub(r"\s+", " ", s)
    return s.strip()





def parse_reference_education(text: str) -> list[EducationItem]:
    """Parse semicolon-delimited education strings from reference screens."""
    items: list[EducationItem] = []
    for entry in text.split(";"):
        cleaned = clean_text(entry)
        if not cleaned:
            continue
        m_year = re.search(r"\((\d{4})\)", cleaned)
        year = m_year.group(1) if m_year else ""
        deg_inst = re.sub(r"\s*\(\d{4}\)", "", cleaned).strip()
        parts = re.split(r"\s+[–\-]\s+", deg_inst)
        if len(parts) >= 2:
            degree_field = parts[0].strip()
            school = parts[1].strip()
        else:
            degree_field = ""
            school = deg_inst
        items.append(
            EducationItem(
                school=school,
                degree=degree_field,
                start_year="",
                end_year=year,
            )
        )
    return items


def parse_reference_experience(text: str) -> list[ExperienceTimelineItem]:
    """Parse semicolon-delimited experience strings from reference screens."""
    items: list[ExperienceTimelineItem] = []
    for entry in text.split(";"):
        cleaned = clean_text(entry)
        if not cleaned:
            continue
        m_years = re.search(r"\((\d{4}(?:[–\-](?:\d{4}|present))?)\)", cleaned, re.IGNORECASE)
        duration = m_years.group(1) if m_years else ""
        clean_entry = re.sub(r"\s*\([^)]+\)", "", cleaned).strip()
        parts = [p.strip() for p in clean_entry.split(",")]
        if len(parts) >= 2:
            title = parts[0]
            company = ", ".join(parts[1:])
        else:
            title = clean_entry
            company = ""
        items.append(
            ExperienceTimelineItem(
                title=title,
                company=company,
                duration=duration,
            )
        )
    return items


def extract_profiles_from_reference_file(file_path: Path) -> list[FounderProfile]:
    """Extract founder profiles from a canonical reference/*.json screen."""
    with open(file_path, "r", encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)

    canonical: dict[str, Any] = data.get("canonical", {}).get("content", {})
    cover: dict[str, Any] = canonical.get("cover", {})
    company_name: str = clean_text(cover.get("company_name", ""))
    research_cutoff: str = clean_text(cover.get("research_cutoff", "Unknown Date"))

    profiles: list[FounderProfile] = []
    sections: list[dict[str, Any]] = canonical.get("sections", [])

    for s in sections:
        if s.get("key") != "team":
            continue
        for row in s.get("blocks", []):
            if not isinstance(row, list) or len(row) < 3:
                continue
            block_type = row[0]
            if block_type != "cards":
                continue
            cards_list = row[2]
            if not isinstance(cards_list, list):
                continue

            for card in cards_list:
                if not isinstance(card, dict):
                    continue
                name = clean_text(card.get("name", ""))
                if not name:
                    continue
                role = clean_text(card.get("role", ""))
                fit = clean_text(card.get("fit", ""))
                lines: list[Any] = card.get("lines", [])

                edu_items: list[EducationItem] = []
                exp_items: list[ExperienceTimelineItem] = []

                for line in lines:
                    if not isinstance(line, (list, tuple)) or len(line) < 2:
                        continue
                    label, content = line[0], line[1]
                    if not isinstance(content, str):
                        continue
                    label_clean = str(label).lower()
                    if "education" in label_clean:
                        edu_items.extend(parse_reference_education(content))
                    elif "experience" in label_clean or "roles" in label_clean:
                        exp_items.extend(parse_reference_experience(content))

                sections_avail: list[str] = []
                if fit:
                    sections_avail.append("summary")
                if exp_items:
                    sections_avail.append("experience")
                if edu_items:
                    sections_avail.append("education")

                slug = generate_founder_slug(name, company_name)
                source_label = f"From vSET reference screen, {research_cutoff}"

                profile = FounderProfile(
                    id=uuid4(),
                    slug=slug,
                    founder_name=name,
                    company_name=company_name,
                    headline=role or None,
                    location=None,
                    about=fit or None,
                    linkedin_url=None,
                    experience_timeline=exp_items,
                    education=edu_items,
                    skills=[],
                    certifications=[],
                    languages=[],
                    retrieval=RetrievalPayload(
                        status="reference_screen",
                        source_type="reference_screen",
                        source_id=f"reference_{slug}",
                        sections_available=sections_avail,
                        warnings=[],
                        verification_reason=f"Imported from verified vSET reference screen for {company_name}",
                        source_label=source_label,
                    ),
                    identity_status="verified",
                    notes=f"Reference screen cutoff: {research_cutoff}",
                )
                profiles.append(profile)

    return profiles


def discover_reference_files(reference_dir: Path) -> list[Path]:
    """Find only canonical reference json files, skipping auto-discovered companies."""
    if not reference_dir.exists():
        logger.error("Reference directory %s does not exist", reference_dir)
        return []
    # Match only canonical reference screens: mysa_founder_screen.json, terraspark_founder_screen.json
    candidates = sorted(reference_dir.glob("*_founder_screen.json"))
    return candidates


async def run_migration(dry_run: bool = True) -> list[FounderProfile]:
    """Execute or dry-run the migration of reference founder profiles."""
    ref_dir = root_dir / "reference"
    files = discover_reference_files(ref_dir)
    if not files:
        print(f"No reference screen files found in {ref_dir}.")
        return []

    all_profiles: list[FounderProfile] = []
    for f in files:
        profiles = extract_profiles_from_reference_file(f)
        all_profiles.extend(profiles)

    # Print dry-run report
    print("\n" + "=" * 80)
    mode_str = "DRY-RUN (NO CHANGES WRITTEN)" if dry_run else "EXECUTE (WRITING TO DB)"
    print(f"  FOUNDER PROFILES MIGRATION: {mode_str}")
    print("=" * 80)
    print(f"Source: {ref_dir} (canonical reference screens ONLY)")
    print(f"Total reference files parsed: {len(files)}")
    print(f"Total founder profiles extracted: {len(all_profiles)}\n")

    for i, p in enumerate(all_profiles, 1):
        print(f"[{i}] {p.founder_name} ({p.company_name or 'N/A'})")
        print(f"    Slug:            {p.slug}")
        print(f"    Headline/Role:   {p.headline or 'N/A'}")
        print(f"    Identity Status: {p.identity_status}")
        print(f"    Source Label:    {p.retrieval.source_label}")
        print(f"    Experience:      {len(p.experience_timeline)} roles")
        for exp in p.experience_timeline:
            print(f"      * {exp.title} - {exp.company} ({exp.duration})")
        print(f"    Education:       {len(p.education)} records")
        for edu in p.education:
            print(f"      * {edu.degree + ' ' if edu.degree else ''}{edu.school} ({edu.end_year})")
        if p.about:
            preview = p.about[:100] + "..." if len(p.about) > 100 else p.about
            print(f"    About:           {preview}")
        print("-" * 80)

    if dry_run:
        print("\n[DRY RUN COMPLETE] Zero database writes performed.")
        print("To write these profiles into the database, re-run with '--execute'.\n")
        return all_profiles

    # If --execute was specified:
    print("\nPersisting profiles to database...")
    await init_db()
    async with async_session_factory() as session:
        repo = SqliteFounderProfileRepository(session)
        created_count = 0
        for p in all_profiles:
            existing = await repo.find_by_slug(p.slug)
            if existing:
                print(f"Skipping {p.slug}: profile already exists.")
                continue
            await repo.save(p)
            created_count += 1
        print(f"Successfully migrated {created_count} profiles to the database.\n")

    return all_profiles


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate founder profiles strictly from reference/*.json screens."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Simulate migration without modifying the database (default).",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        default=False,
        help="Execute database writes (requires explicit confirmation).",
    )
    args = parser.parse_args()

    is_dry_run = not args.execute
    asyncio.run(run_migration(dry_run=is_dry_run))


if __name__ == "__main__":
    main()
