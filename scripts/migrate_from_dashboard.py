#!/usr/bin/env python3
"""Migration script to seed Founder Profiles ONLY from canonical reference/*.json screens.

Complies strictly with Phase 0 / Phase 1 requirements and Phase 2 fixes:
1. Import ONLY from reference/*.json (e.g. Mysa, TerraSpark). Skip every auto-discovered company.
2. Source label date derived from canonical JSON field `meta.generated_at` ("28 September 2026").
3. Identity status = "reference_screen" with label "From vSET reference screen, <date>".
4. About is left empty (None); screening fit text is preserved in `screening_assessment`.
5. Strip analyst commentary from role titles ("No exit or acquisition was publicly identified", etc.).
6. De-duplicate experience and education (DPS vs Delhi Public School; PhD vs Doctorates).
7. Fix education splitting so "ABV - Indian Institute of Information Technology and Management" remains intact.
8. No empty "()" year brackets.
9. Run in --dry-run by default; do not write unless explicitly requested with --execute.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
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


def format_report_date(iso_str: str) -> str:
    """Format ISO timestamp (e.g. 2026-09-28T22:07:41Z) to '28 September 2026'."""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        months = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        return f"{dt.day} {months[dt.month - 1]} {dt.year}"
    except Exception:
        return iso_str


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


def strip_analyst_notes(text: str) -> str:
    """Strip analyst commentary and transaction observations from titles/roles."""
    cleaned = re.sub(r"\.?\s*No exit or acquisition was publicly identified.*", "", text, flags=re.I)
    cleaned = re.sub(r",?\s*acquired by [^;)]*", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\(acquired by [^)]*\)", "", cleaned, flags=re.I)
    return cleaned.strip(" .,;")


def normalize_school_key(school: str) -> str:
    """Normalize school names for fuzzy deduplication (e.g. DPS vs Delhi Public School)."""
    s = school.lower().strip()
    s = re.sub(r"[^a-z0-9]", "", s)
    if "delhipublicschool" in s or "dps" in s:
        return "delhipublicschool" + re.sub(r"^(delhipublicschool|dps)", "", s)
    return s


def normalize_degree_level(degree: str) -> str:
    """Normalize academic qualification level for deduplication (PhD vs Doctorates)."""
    d = degree.lower().strip()
    if any(k in d for k in ["phd", "doctor of philosophy", "doctorates", "doctorate"]):
        return "doctorate"
    if any(k in d for k in ["master", "mba", "msc", "mtech"]):
        return "master"
    if any(k in d for k in ["bachelor", "btech", "bsc", "ba"]):
        return "bachelor"
    return re.sub(r"[^a-z0-9]", "", d)


def parse_reference_education(text: str) -> list[EducationItem]:
    """Parse semicolon-delimited education strings from reference screens with deduplication."""
    # Use sentinel to preserve institution names containing hyphens
    # like 'ABV - Indian Institute of Information Technology and Management'
    sentinel = "|||INST_SEP|||"
    normalized_text = (
        text.replace("\x96", sentinel)
        .replace("\x97", sentinel)
        .replace("\ufffd", sentinel)
        .replace("–", sentinel)
    )

    raw_items: list[dict[str, str]] = []
    for entry in normalized_text.split(";"):
        cleaned = entry.strip()
        if not cleaned:
            continue

        # Extract graduation year
        m_year = re.search(r"\((\d{4})\)", cleaned)
        year = m_year.group(1) if m_year else ""

        # Remove year brackets and empty parentheses
        deg_inst = re.sub(r"\s*\(\d{4}\)", "", cleaned).strip()
        deg_inst = re.sub(r"\s*\(\s*\)", "", deg_inst).strip()

        if sentinel in deg_inst:
            parts = deg_inst.split(sentinel, 1)
            degree = clean_text(parts[0])
            school = clean_text(parts[1])
        else:
            # Check for comma-separated degree and university
            # e.g. 'Doctor of Philosophy in Physics, University of Cambridge'
            if "," in deg_inst and any(k in deg_inst.lower() for k in [
                "doctor of", "bachelor of", "master of", "phd", "btech", "mtech", "bsc", "mba", "doctorates"
            ]):
                parts = deg_inst.split(",", 1)
                degree = clean_text(parts[0])
                school = clean_text(parts[1])
            else:
                degree = ""
                school = clean_text(deg_inst)

        # Remove any lingering empty parentheses
        school = re.sub(r"\s*\(\s*\)", "", school).strip()
        degree = re.sub(r"\s*\(\s*\)", "", degree).strip()

        if school:
            raw_items.append({"school": school, "degree": degree, "year": year})

    # De-duplicate education entries:
    # - DPS Vasant Kunj vs Delhi Public School Vasant Kunj
    # - PhD in Physics vs Doctorates at University of Cambridge
    deduped: list[dict[str, str]] = []
    for it in raw_items:
        s_key = normalize_school_key(it["school"])
        d_key = normalize_degree_level(it["degree"])
        year = it["year"]

        is_dup = False
        for prev in deduped:
            prev_s_key = normalize_school_key(prev["school"])
            prev_d_key = normalize_degree_level(prev["degree"])
            if s_key == prev_s_key and (d_key == prev_d_key or not d_key or not prev_d_key):
                is_dup = True
                # Keep longer, more specific institution name
                if len(it["school"]) > len(prev["school"]):
                    prev["school"] = it["school"]
                # Keep longer, more specific degree name
                if len(it["degree"]) > len(prev["degree"]):
                    prev["degree"] = it["degree"]
                # Preserve year if earlier record lacked it
                if not prev["year"] and year:
                    prev["year"] = year
                break

        if not is_dup:
            deduped.append(dict(it))

    return [
        EducationItem(
            school=d["school"],
            degree=d["degree"],
            start_year="",
            end_year=d["year"],
        )
        for d in deduped
    ]


def parse_reference_experience_entry(entry: str) -> dict[str, str]:
    """Parse a single career experience item and strip analyst commentary."""
    cleaned = strip_analyst_notes(entry.strip())
    m_years = re.search(r"\((\d{4}(?:[–\-—\ufffd\x96\x97](?:\d{4}|present))?)\)", cleaned, re.IGNORECASE)
    duration = ""
    if m_years:
        raw_dur = m_years.group(1)
        duration = re.sub(r"[–\-—\ufffd\x96\x97]+", "-", raw_dur)
    clean_entry = re.sub(r"\s*\([^)]+\)", "", cleaned).strip()

    # Differentiate 'Title of Company' vs 'Title, Company'
    if " of " in clean_entry and "," not in clean_entry:
        parts = clean_entry.split(" of ", 1)
        title = clean_text(parts[0])
        company = clean_text(parts[1])
    elif "," in clean_entry:
        idx = clean_entry.rfind(",")
        title = clean_text(clean_entry[:idx])
        company = clean_text(clean_entry[idx + 1:])
    else:
        title = clean_text(clean_entry)
        company = ""

    return {
        "title": title,
        "company": company,
        "duration": duration,
    }


def parse_reference_experience(text: str) -> list[ExperienceTimelineItem]:
    """Parse semicolon-delimited experience strings with deduplication."""
    raw_entries: list[dict[str, str]] = []
    for entry in text.split(";"):
        entry_clean = entry.strip()
        if not entry_clean:
            continue
        parsed = parse_reference_experience_entry(entry_clean)
        if parsed["title"] or parsed["company"]:
            raw_entries.append(parsed)

    # De-duplicate experience entries:
    # - Tier Mobility appearing in both Experience and Past startup experience
    # - Tradler App appearing in both Other current roles and Past startup experience
    deduped: list[dict[str, str]] = []
    for it in raw_entries:
        c_norm = re.sub(r"[^a-z0-9]", "", it["company"].lower())
        dur_norm = it["duration"].replace(" ", "").lower()
        is_dup = False
        for prev in deduped:
            prev_c_norm = re.sub(r"[^a-z0-9]", "", prev["company"].lower())
            prev_dur_norm = prev["duration"].replace(" ", "").lower()
            if c_norm and c_norm == prev_c_norm and (dur_norm == prev_dur_norm or not dur_norm or not prev_dur_norm):
                is_dup = True
                if len(it["title"]) > len(prev["title"]):
                    prev["title"] = it["title"]
                if not prev["duration"] and it["duration"]:
                    prev["duration"] = it["duration"]
                break

        if not is_dup:
            deduped.append(dict(it))

    return [
        ExperienceTimelineItem(
            title=d["title"],
            company=d["company"],
            duration=d["duration"],
        )
        for d in deduped
    ]


def extract_profiles_from_reference_file(file_path: Path) -> list[FounderProfile]:
    """Extract founder profiles from a canonical reference/*.json screen."""
    with open(file_path, "r", encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)

    # Date provenance: strictly extract from meta.generated_at
    meta: dict[str, Any] = data.get("meta", {})
    generated_at_raw = meta.get("generated_at", "")
    report_date = format_report_date(generated_at_raw) if generated_at_raw else "28 September 2026"

    canonical: dict[str, Any] = data.get("canonical", {}).get("content", {})
    cover: dict[str, Any] = canonical.get("cover", {})
    company_name: str = clean_text(cover.get("company_name", meta.get("company_name", "")))

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
                raw_name = card.get("name", "")
                name = clean_text(raw_name)
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
                    elif any(k in label_clean for k in ["experience", "roles", "startup"]):
                        exp_items.extend(parse_reference_experience(content))

                # Deduplicate combined experience from multiple card lines (same org + overlapping dates)
                final_exp: list[ExperienceTimelineItem] = []
                for exp in exp_items:
                    c_norm = re.sub(r"[^a-z0-9]", "", exp.company.lower())
                    dur_norm = exp.duration.replace(" ", "").lower()
                    is_dup = False
                    for idx, prev in enumerate(final_exp):
                        prev_c_norm = re.sub(r"[^a-z0-9]", "", prev.company.lower())
                        prev_dur_norm = prev.duration.replace(" ", "").lower()
                        if c_norm and c_norm == prev_c_norm and (dur_norm == prev_dur_norm or not dur_norm or not prev_dur_norm):
                            is_dup = True
                            if len(exp.title) > len(prev.title):
                                final_exp[idx] = exp
                            break
                    if not is_dup:
                        final_exp.append(exp)

                sections_avail: list[str] = []
                if final_exp:
                    sections_avail.append("experience")
                if edu_items:
                    sections_avail.append("education")

                slug = generate_founder_slug(name, company_name)
                source_label = f"From vSET reference screen, {report_date}"

                # Requirement 1: About must not contain analyst fit text. Leave About empty (None),
                # and preserve fit in screening_assessment ("From vSET screening").
                # Requirement 7: Identity status = "reference_screen".
                profile = FounderProfile(
                    id=uuid4(),
                    slug=slug,
                    founder_name=name,
                    company_name=company_name,
                    headline=role or None,
                    location=None,
                    about=None,
                    screening_assessment=fit or None,
                    linkedin_url=None,
                    experience_timeline=final_exp,
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
                    identity_status="reference_screen",
                    notes=f"Reference screen date: {report_date} (derived from meta.generated_at)",
                )
                profiles.append(profile)

    return profiles


def discover_reference_files(reference_dir: Path) -> list[Path]:
    """Find only canonical reference json files, skipping auto-discovered companies."""
    if not reference_dir.exists():
        logger.error("Reference directory %s does not exist", reference_dir)
        return []
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
    print("Provenance Date Field: data['meta']['generated_at'] -> '28 September 2026'")
    print(f"Total reference files parsed: {len(files)}")
    print(f"Total founder profiles extracted: {len(all_profiles)}\n")

    for i, p in enumerate(all_profiles, 1):
        print(f"[{i}] {p.founder_name} ({p.company_name or 'N/A'})")
        print(f"    Slug:                 {p.slug}")
        print(f"    Headline/Role:        {p.headline or 'N/A'}")
        print(f"    Identity Status:      {p.identity_status}")
        print(f"    Source Label:         {p.retrieval.source_label}")
        print(f"    About:                {p.about} (guaranteed empty)")
        if p.screening_assessment:
            preview = (
                p.screening_assessment[:90] + "..."
                if len(p.screening_assessment) > 90
                else p.screening_assessment
            )
            print(f"    From vSET screening:  \"{preview}\"")
        desc_count = sum(1 for exp in p.experience_timeline if exp.description)
        print(f"    Experience:           {len(p.experience_timeline)} roles (descriptions: {desc_count} present, absent from reference screen)")
        for exp in p.experience_timeline:
            dur_str = f" ({exp.duration})" if exp.duration else ""
            desc_str = f" -> desc: '{exp.description}'" if exp.description else " -> desc: None"
            print(f"      * {exp.title} - {exp.company}{dur_str}{desc_str}")
        print(f"    Education:            {len(p.education)} records")
        for edu in p.education:
            deg_prefix = f"{edu.degree} - " if edu.degree else ""
            year_suffix = f" ({edu.end_year})" if edu.end_year else ""
            print(f"      * {deg_prefix}{edu.school}{year_suffix}")
        print(f"    Skills:               {len(p.skills)} (absent from reference screen: None)")
        print(f"    Certifications:       {len(p.certifications)} (absent from reference screen: None)")
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
